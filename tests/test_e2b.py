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

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.run_code.return_value = mock_exec

    result = await e2b_runtime.execute("plot()", "python")

    assert len(result.artifacts) == 1
    assert result.artifacts[0].content_type == "image/png"
    assert result.artifacts[0].url is not None and "base64,base64data" in result.artifacts[0].url


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
async def test_upload_success(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    local_file = tmp_path / "test.txt"
    local_file.write_text("content")

    await e2b_runtime.upload(local_file, "remote.txt")

    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.write.assert_called()


@pytest.mark.asyncio
async def test_download_success(e2b_runtime: E2BRuntime, tmp_path: Any) -> None:
    assert e2b_runtime.sandbox is not None
    e2b_runtime.sandbox.files.read.return_value = b"content"

    dest = tmp_path / "downloaded.txt"
    await e2b_runtime.download("remote.txt", dest)

    assert dest.read_text() == "content"


@pytest.mark.asyncio
async def test_terminate_success(e2b_runtime: E2BRuntime) -> None:
    # Capture the sandbox mock before terminate clears it
    sandbox_mock = e2b_runtime.sandbox
    assert sandbox_mock is not None

    await e2b_runtime.terminate()
    sandbox_mock.close.assert_called_once()
    assert e2b_runtime.sandbox is None
