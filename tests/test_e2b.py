import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from coreason_sandbox.runtimes.e2b import E2BRuntime


@pytest.fixture
def mock_e2b_sandbox() -> Any:
    with patch("coreason_sandbox.runtimes.e2b.E2BSandbox") as mock:
        yield mock


@pytest.fixture
def e2b_runtime(mock_e2b_sandbox: Any) -> E2BRuntime:
    runtime = E2BRuntime(api_key="test_key")
    # Manually set sandbox as if started
    runtime.sandbox = mock_e2b_sandbox.return_value
    runtime.sandbox.sandbox_id = "e2b_id"
    return runtime


@pytest.mark.asyncio
async def test_start_success(mock_e2b_sandbox: Any) -> None:
    runtime = E2BRuntime(api_key="key")
    await runtime.start()
    mock_e2b_sandbox.assert_called_once()
    assert runtime.sandbox is not None


@pytest.mark.asyncio
async def test_start_failure(mock_e2b_sandbox: Any) -> None:
    mock_e2b_sandbox.side_effect = Exception("Start failed")
    runtime = E2BRuntime(api_key="key")
    with pytest.raises(Exception, match="Start failed"):
        await runtime.start()


@pytest.mark.asyncio
async def test_execute_python_success(e2b_runtime: E2BRuntime) -> None:
    # Mock execution result
    mock_exec = MagicMock()
    mock_exec.logs.stdout = [MagicMock(content="hello")]
    mock_exec.logs.stderr = []
    mock_exec.error = None
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    result = await e2b_runtime.execute("print('hello')", "python")

    e2b_runtime.sandbox.run_code.assert_called_with("print('hello')")
    assert result.stdout == "hello"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_python_error(e2b_runtime: E2BRuntime) -> None:
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = MagicMock(name="NameError", value="msg", traceback="tb")
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    result = await e2b_runtime.execute("error", "python")
    assert result.exit_code == 1
    assert "NameError" in result.stderr


@pytest.mark.asyncio
async def test_execute_python_artifacts(e2b_runtime: E2BRuntime) -> None:
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = None

    # Mock png result
    result_obj = MagicMock()
    result_obj.png = "base64data"
    result_obj.text = None
    mock_exec.results = [result_obj]

    # Mock text result
    text_obj = MagicMock()
    text_obj.png = None
    text_obj.text = "output"
    mock_exec.results.append(text_obj)

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    result = await e2b_runtime.execute("plot()", "python")

    assert len(result.artifacts) == 1
    assert result.artifacts[0].content_type == "image/png"
    assert result.artifacts[0].url is not None and "base64,base64data" in result.artifacts[0].url
    assert "output" in result.stdout


@pytest.mark.asyncio
async def test_execute_python_filesystem_artifacts(e2b_runtime: E2BRuntime) -> None:
    """Test detection of filesystem artifacts (e.g. CSV files)."""
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = None
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    # Mock list_files to return empty list first, then list with new file
    entry1 = MagicMock()
    entry1.name = "existing.txt"
    entry2 = MagicMock()
    entry2.name = "new.csv"

    e2b_runtime.sandbox.files.list.side_effect = [
        [entry1],  # Before
        [entry1, entry2],  # After
    ]

    # Mock download
    e2b_runtime.sandbox.files.read.return_value = b"csv_content"

    result = await e2b_runtime.execute("create_csv()", "python")

    assert len(result.artifacts) == 1
    assert result.artifacts[0].filename == "new.csv"
    assert result.artifacts[0].content_type == "text/csv"  # inferred from extension
    # Verify download called
    e2b_runtime.sandbox.files.read.assert_called_with("new.csv")


@pytest.mark.asyncio
async def test_execute_bash_success(e2b_runtime: E2BRuntime) -> None:
    mock_cmd = MagicMock()
    mock_cmd.stdout = "root"
    mock_cmd.stderr = ""
    mock_cmd.exit_code = 0
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.commands.run.return_value = mock_cmd

    result = await e2b_runtime.execute("whoami", "bash")

    e2b_runtime.sandbox.commands.run.assert_called_with("whoami")
    assert result.stdout == "root"


@pytest.mark.asyncio
async def test_execute_r_success(e2b_runtime: E2BRuntime) -> None:
    mock_cmd = MagicMock()
    mock_cmd.stdout = "[1] 4"
    mock_cmd.stderr = ""
    mock_cmd.exit_code = 0
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.commands.run.return_value = mock_cmd

    result = await e2b_runtime.execute("2+2", "r")

    e2b_runtime.sandbox.commands.run.assert_called_with("Rscript -e '2+2'")
    assert result.stdout == "[1] 4"


@pytest.mark.asyncio
async def test_execute_unsupported(e2b_runtime: E2BRuntime) -> None:
    with pytest.raises(ValueError):
        await e2b_runtime.execute("code", "java")  # type: ignore


@pytest.mark.asyncio
async def test_execute_exception(e2b_runtime: E2BRuntime) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.side_effect = Exception("Fail")
    with pytest.raises(Exception, match="Fail"):
        await e2b_runtime.execute("code", "python")


@pytest.mark.asyncio
async def test_execute_no_sandbox(mock_e2b_sandbox: Any) -> None:
    runtime = E2BRuntime()
    with pytest.raises(RuntimeError):
        await runtime.execute("code", "python")


@pytest.mark.asyncio
async def test_upload_success(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    local_file = tmp_path / "test.txt"
    local_file.write_text("content")

    await e2b_runtime.upload(local_file, "remote.txt")

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.write.assert_called()


@pytest.mark.asyncio
async def test_upload_no_file(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    local_file = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        await e2b_runtime.upload(local_file, "remote.txt")


@pytest.mark.asyncio
async def test_upload_exception(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    local_file = tmp_path / "test.txt"
    local_file.write_text("content")
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.write.side_effect = Exception("Fail")

    with pytest.raises(Exception, match="Fail"):
        await e2b_runtime.upload(local_file, "remote.txt")


@pytest.mark.asyncio
async def test_upload_no_sandbox(tmp_path: Any) -> None:
    runtime = E2BRuntime()
    local_file = tmp_path / "test.txt"
    with pytest.raises(RuntimeError):
        await runtime.upload(local_file, "remote.txt")


@pytest.mark.asyncio
async def test_download_success(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.read.return_value = b"content"

    dest = tmp_path / "downloaded.txt"
    await e2b_runtime.download("remote.txt", dest)

    assert dest.read_text() == "content"


@pytest.mark.asyncio
async def test_download_not_found(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.read.return_value = None

    dest = tmp_path / "downloaded.txt"
    with pytest.raises(FileNotFoundError):
        await e2b_runtime.download("missing.txt", dest)


@pytest.mark.asyncio
async def test_download_exception(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.read.side_effect = Exception("Fail")
    dest = tmp_path / "downloaded.txt"
    with pytest.raises(Exception, match="Fail"):
        await e2b_runtime.download("remote.txt", dest)


@pytest.mark.asyncio
async def test_download_no_sandbox(tmp_path: Any) -> None:
    runtime = E2BRuntime()
    dest = tmp_path / "dest.txt"
    with pytest.raises(RuntimeError):
        await runtime.download("remote.txt", dest)


@pytest.mark.asyncio
async def test_terminate_success(e2b_runtime: E2BRuntime) -> None:
    # Capture the sandbox mock before terminate clears it
    sandbox_mock = e2b_runtime.sandbox
    assert sandbox_mock is not None

    await e2b_runtime.terminate()
    sandbox_mock.close.assert_called_once()
    assert e2b_runtime.sandbox is None


@pytest.mark.asyncio
async def test_terminate_exception(e2b_runtime: E2BRuntime) -> None:
    sandbox_mock = e2b_runtime.sandbox
    assert sandbox_mock is not None
    sandbox_mock.close.side_effect = Exception("Fail")

    # Should not raise exception
    await e2b_runtime.terminate()

    assert e2b_runtime.sandbox is None


@pytest.mark.asyncio
async def test_terminate_no_sandbox() -> None:
    runtime = E2BRuntime()
    await runtime.terminate()


@pytest.mark.asyncio
async def test_install_package_success(e2b_runtime: E2BRuntime) -> None:
    assert e2b_runtime.sandbox is not None
    await e2b_runtime.install_package("requests")
    e2b_runtime.sandbox.commands.run.assert_called_with("pip install requests")


@pytest.mark.asyncio
async def test_install_package_exception(e2b_runtime: E2BRuntime) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.commands.run.side_effect = Exception("Fail")
    with pytest.raises(Exception, match="Fail"):
        await e2b_runtime.install_package("requests")


@pytest.mark.asyncio
async def test_install_package_no_sandbox() -> None:
    runtime = E2BRuntime()
    with pytest.raises(RuntimeError):
        await runtime.install_package("req")


@pytest.mark.asyncio
async def test_list_files_success(e2b_runtime: E2BRuntime) -> None:
    assert e2b_runtime.sandbox is not None
    entry = MagicMock()
    entry.name = "file.txt"
    e2b_runtime.sandbox.files.list.return_value = [entry]

    files = await e2b_runtime.list_files(".")
    assert files == ["file.txt"]


@pytest.mark.asyncio
async def test_list_files_exception(e2b_runtime: E2BRuntime) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.list.side_effect = Exception("Fail")

    files = await e2b_runtime.list_files(".")
    assert files == []


@pytest.mark.asyncio
async def test_list_files_internal_exception(e2b_runtime: E2BRuntime) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.list.side_effect = Exception("Fail")

    files = await e2b_runtime._list_files_internal(".")
    assert files == set()


@pytest.mark.asyncio
async def test_list_files_internal_no_sandbox() -> None:
    runtime = E2BRuntime()
    files = await runtime._list_files_internal(".")
    assert files == set()


@pytest.mark.asyncio
async def test_execute_python_artifact_retrieval_exception(e2b_runtime: E2BRuntime) -> None:
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = None
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    entry1 = MagicMock()
    entry1.name = "new.csv"
    e2b_runtime.sandbox.files.list.side_effect = [
        [],  # Before
        [entry1],  # After
    ]

    e2b_runtime.sandbox.files.read.side_effect = Exception("Download Fail")

    result = await e2b_runtime.execute("create()", "python")

    assert len(result.artifacts) == 0
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_list_files_no_sandbox() -> None:
    runtime = E2BRuntime()
    with pytest.raises(RuntimeError):
        await runtime.list_files(".")


@pytest.mark.asyncio
async def test_execute_python_multiple_artifacts_with_spaces(e2b_runtime: E2BRuntime) -> None:
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = None
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    entry1 = MagicMock()
    entry1.name = "data.csv"
    entry2 = MagicMock()
    entry2.name = "my chart.png"
    entry3 = MagicMock()
    entry3.name = "notes.txt"

    e2b_runtime.sandbox.files.list.side_effect = [
        [],  # Before
        [entry1, entry2, entry3],  # After
    ]

    def side_effect_read(path: str) -> bytes | None:
        if path == "data.csv":
            return b"csv"
        if path == "my chart.png":
            return b"png"
        if path == "notes.txt":
            return b"notes"
        return None

    e2b_runtime.sandbox.files.read.side_effect = side_effect_read

    result = await e2b_runtime.execute("create_multiple()", "python")

    assert len(result.artifacts) == 3
    filenames = {a.filename for a in result.artifacts}
    assert filenames == {"data.csv", "my chart.png", "notes.txt"}


@pytest.mark.asyncio
async def test_execute_file_deletion_and_modification(e2b_runtime: E2BRuntime) -> None:
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = None
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    entry_existing = MagicMock()
    entry_existing.name = "config.json"
    entry_modified = MagicMock()
    entry_modified.name = "data.csv"

    e2b_runtime.sandbox.files.list.side_effect = [
        [entry_existing, entry_modified],  # Before
        [entry_modified],  # After (config.json gone)
    ]

    e2b_runtime.sandbox.files.read.return_value = b"content"

    result = await e2b_runtime.execute("delete_and_modify()", "python")

    assert len(result.artifacts) == 0


@pytest.mark.asyncio
async def test_execute_python_timeout(e2b_runtime: E2BRuntime) -> None:
    """Test that execution enforces timeout."""
    e2b_runtime.timeout = 0.1

    def long_running_code(*args: Any, **kwargs: Any) -> Any:
        time.sleep(0.2)
        return MagicMock()

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.side_effect = long_running_code

    with pytest.raises(TimeoutError, match="Execution exceeded 0.1 seconds limit"):
        await e2b_runtime.execute("while True: pass", "python")


@pytest.mark.asyncio
async def test_execute_bash_timeout(e2b_runtime: E2BRuntime) -> None:
    """Test that bash execution enforces timeout."""
    e2b_runtime.timeout = 0.1

    def long_running_code(*args: Any, **kwargs: Any) -> Any:
        time.sleep(0.2)
        return MagicMock()

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.commands.run.side_effect = long_running_code

    with pytest.raises(TimeoutError, match="Execution exceeded 0.1 seconds limit"):
        await e2b_runtime.execute("sleep 10", "bash")


@pytest.mark.asyncio
async def test_execute_r_timeout(e2b_runtime: E2BRuntime) -> None:
    """Test that R execution enforces timeout."""
    e2b_runtime.timeout = 0.1

    def long_running_code(*args: Any, **kwargs: Any) -> Any:
        time.sleep(0.2)
        return MagicMock()

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.commands.run.side_effect = long_running_code

    with pytest.raises(TimeoutError, match="Execution exceeded 0.1 seconds limit"):
        await e2b_runtime.execute("Sys.sleep(10)", "r")


@pytest.mark.asyncio
async def test_start_idempotency_with_restart(e2b_runtime: E2BRuntime) -> None:
    """Test that calling start() on a running sandbox terminates the old one first."""
    assert e2b_runtime.sandbox is not None
    old_sandbox = e2b_runtime.sandbox

    # Mock close to verify it's called
    old_sandbox.close = MagicMock()

    # We need to mock Sandbox constructor again to return a NEW sandbox
    with patch("coreason_sandbox.runtimes.e2b.E2BSandbox") as mock_new_sandbox_cls:
        new_sandbox_mock = MagicMock()
        new_sandbox_mock.sandbox_id = "new_id"
        mock_new_sandbox_cls.return_value = new_sandbox_mock

        await e2b_runtime.start()

        # Verify old sandbox was closed
        old_sandbox.close.assert_called_once()

        # Verify new sandbox is set
        assert e2b_runtime.sandbox == new_sandbox_mock
        assert e2b_runtime.sandbox.sandbox_id == "new_id"


@pytest.mark.asyncio
async def test_execute_sequential_persistence(e2b_runtime: E2BRuntime) -> None:
    """Verify multiple execute calls use the same sandbox instance."""
    assert e2b_runtime.sandbox is not None
    original_sandbox = e2b_runtime.sandbox

    # Mock result 1
    mock_exec1 = MagicMock()
    mock_exec1.logs.stdout = [MagicMock(content="step1")]
    mock_exec1.logs.stderr = []
    mock_exec1.error = None
    mock_exec1.results = []

    # Mock result 2
    mock_exec2 = MagicMock()
    mock_exec2.logs.stdout = [MagicMock(content="step2")]
    mock_exec2.logs.stderr = []
    mock_exec2.error = None
    mock_exec2.results = []

    e2b_runtime.sandbox.run_code.side_effect = [mock_exec1, mock_exec2]

    # Run 1
    res1 = await e2b_runtime.execute("x=1", "python")
    assert res1.stdout == "step1"

    # Run 2
    res2 = await e2b_runtime.execute("print(x)", "python")
    assert res2.stdout == "step2"

    # Verify sandbox instance didn't change
    assert e2b_runtime.sandbox is original_sandbox
    # Verify run_code called twice on same instance
    assert e2b_runtime.sandbox.run_code.call_count == 2


@pytest.mark.asyncio
async def test_execute_error_persistence(e2b_runtime: E2BRuntime) -> None:
    """Verify non-fatal error doesn't restart sandbox."""
    assert e2b_runtime.sandbox is not None
    original_sandbox = e2b_runtime.sandbox

    # Mock error execution (e.g. syntax error)
    mock_exec_err = MagicMock()
    mock_exec_err.logs.stdout = []
    mock_exec_err.logs.stderr = []
    mock_exec_err.error = MagicMock(name="SyntaxError", value="invalid syntax", traceback="")
    mock_exec_err.results = []

    # Mock success execution
    mock_exec_ok = MagicMock()
    mock_exec_ok.logs.stdout = [MagicMock(content="ok")]
    mock_exec_ok.logs.stderr = []
    mock_exec_ok.error = None
    mock_exec_ok.results = []

    e2b_runtime.sandbox.run_code.side_effect = [mock_exec_err, mock_exec_ok]

    # Run 1 (Error)
    res1 = await e2b_runtime.execute("syntax error", "python")
    assert res1.exit_code == 1

    # Run 2 (OK)
    res2 = await e2b_runtime.execute("print('ok')", "python")
    assert res2.exit_code == 0

    # Verify sandbox instance preserved
    assert e2b_runtime.sandbox is original_sandbox


@pytest.mark.asyncio
async def test_concurrent_terminate_during_execute(e2b_runtime: E2BRuntime) -> None:
    """Simulate terminate being called while execute is waiting."""
    assert e2b_runtime.sandbox is not None

    def side_effect(*args: Any, **kwargs: Any) -> MagicMock:
        time.sleep(0.2)
        return MagicMock(logs=MagicMock(stdout=[], stderr=[]), error=None, results=[])

    e2b_runtime.sandbox.run_code.side_effect = side_effect

    # Start execute task
    exec_task = asyncio.create_task(e2b_runtime.execute("sleep", "python"))

    # Wait a bit then terminate
    await asyncio.sleep(0.05)
    await e2b_runtime.terminate()

    result = await exec_task

    assert e2b_runtime.sandbox is None
    assert result.exit_code == 0
