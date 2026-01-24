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

    # We need to control the sequence of return values for list_files
    # But list_files is an async wrapper or sync? In e2b_runtime it's async wrapper calling sandbox.files.list
    # sandbox.files.list is synchronous in the SDK usually, but let's check wrapper.
    # e2b_runtime.list_files uses sandbox.files.list(path).

    # We need to verify how we can mock 'before' and 'after' calls.
    # If the implementation calls self.list_files("."), we can mock that method on the instance?
    # Or mock sandbox.files.list side_effect.

    e2b_runtime.sandbox.files.list.side_effect = [
        [entry1],  # Before
        [entry1, entry2],  # After
    ]

    # Mock download
    e2b_runtime.sandbox.files.read.return_value = b"csv_content"

    # We expect the implementation to call list_files before and after
    # And then download the new file

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

    # Even if close failed, we expect sandbox reference to be cleared
    # But current implementation (before my fix) might not.
    # The failing test showed it was NOT cleared.
    # I will FIX the implementation in next step.
    # Here I assert that it IS None, assuming I fix it.
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
    # Test _list_files_internal handles exceptions
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.list.side_effect = Exception("Fail")

    # We call _list_files_internal directly to verify it returns empty set
    # Note: access private method for testing
    files = await e2b_runtime._list_files_internal(".")
    assert files == set()


@pytest.mark.asyncio
async def test_list_files_internal_no_sandbox() -> None:
    # Test _list_files_internal when sandbox not started (raises RuntimeError)
    runtime = E2BRuntime()
    files = await runtime._list_files_internal(".")
    assert files == set()


@pytest.mark.asyncio
async def test_execute_python_artifact_retrieval_exception(e2b_runtime: E2BRuntime) -> None:
    """Test handling of artifact retrieval failure."""
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

    # Mock download failure
    e2b_runtime.sandbox.files.read.side_effect = Exception("Download Fail")

    result = await e2b_runtime.execute("create()", "python")

    # Should not fail, just skip artifact
    assert len(result.artifacts) == 0
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_list_files_no_sandbox() -> None:
    runtime = E2BRuntime()
    with pytest.raises(RuntimeError):
        await runtime.list_files(".")


@pytest.mark.asyncio
async def test_execute_python_multiple_artifacts_with_spaces(e2b_runtime: E2BRuntime) -> None:
    """Test detection of multiple files, including those with spaces."""
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = None
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    # Files
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

    # Mock download (return distinct content to verify mapping)
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
    """Verify that deleted or modified files are NOT flagged as new artifacts."""
    mock_exec = MagicMock()
    mock_exec.logs.stdout = []
    mock_exec.logs.stderr = []
    mock_exec.error = None
    mock_exec.results = []

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    # Files
    entry_existing = MagicMock()
    entry_existing.name = "config.json"
    entry_modified = MagicMock()
    entry_modified.name = "data.csv"

    # Before: config.json exists, data.csv exists
    # After: config.json deleted, data.csv modified (still exists), new.txt created

    e2b_runtime.sandbox.files.list.side_effect = [
        [entry_existing, entry_modified],  # Before
        [entry_modified],  # After (config.json gone)
    ]

    # Mock download
    e2b_runtime.sandbox.files.read.return_value = b"content"

    result = await e2b_runtime.execute("delete_and_modify()", "python")

    # new_files = {data.csv} - {config.json, data.csv} = {}
    # So no artifacts should be detected (modification not detected by name diff)
    assert len(result.artifacts) == 0
