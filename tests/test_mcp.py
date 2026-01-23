from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from coreason_sandbox.mcp import SandboxMCP
from coreason_sandbox.models import ExecutionResult, FileReference


@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    runtime.terminate = AsyncMock()
    runtime.execute = AsyncMock()
    runtime.install_package = AsyncMock()
    runtime.list_files = AsyncMock()
    return runtime


@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.mcp.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.fixture
def mock_veritas() -> Any:
    with patch("coreason_sandbox.mcp.VeritasIntegrator") as mock:
        mock.return_value.log_pre_execution = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_mcp_execute_code(mock_factory: Any, mock_runtime: Any, mock_veritas: Any) -> None:
    mcp = SandboxMCP()

    mock_runtime.execute.return_value = ExecutionResult(
        stdout="out",
        stderr="err",
        exit_code=0,
        artifacts=[FileReference(filename="plot.png", path="p", url="http://url")],
        execution_duration=1.0,
    )

    result = await mcp.execute_code("python", "print('hi')")

    # Verify auto-start
    mock_runtime.start.assert_called_once()
    assert mcp.started is True

    # Verify Veritas logging
    mock_veritas.return_value.log_pre_execution.assert_called_with("print('hi')", "python")

    # Verify Execution
    mock_runtime.execute.assert_called_with("print('hi')", "python")

    # Verify output format
    assert result["stdout"] == "out"
    # Need to cast or help mypy understand the structure
    artifacts = cast(list[dict[str, Any]], result["artifacts"])
    assert artifacts[0]["url"] == "http://url"


@pytest.mark.asyncio
async def test_mcp_install_package(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()

    resp = await mcp.install_package("requests")

    mock_runtime.start.assert_called_once()
    mock_runtime.install_package.assert_called_with("requests")
    assert "installed successfully" in resp


@pytest.mark.asyncio
async def test_mcp_list_files(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()
    mock_runtime.list_files.return_value = ["file1", "file2"]

    files = await mcp.list_files("/home")

    mock_runtime.start.assert_called_once()
    mock_runtime.list_files.assert_called_with("/home")
    assert files == ["file1", "file2"]


@pytest.mark.asyncio
async def test_mcp_shutdown(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()
    await mcp.ensure_started()

    await mcp.shutdown()

    mock_runtime.terminate.assert_called_once()
    assert mcp.started is False


@pytest.mark.asyncio
async def test_mcp_shutdown_not_started(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()
    await mcp.shutdown()
    mock_runtime.terminate.assert_not_called()
