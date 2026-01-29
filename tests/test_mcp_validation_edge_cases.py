from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from coreason_sandbox.mcp import SandboxMCP
from coreason_sandbox.models import ExecutionResult


@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    runtime.terminate = AsyncMock()
    runtime.execute.return_value = ExecutionResult(
        stdout="", stderr="", exit_code=0, artifacts=[], execution_duration=0.1
    )
    return runtime


@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.session_manager.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_veritas() -> Any:
    with patch("coreason_sandbox.mcp.VeritasIntegrator") as mock:
        mock.return_value.log_pre_execution = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_mcp_validation_none_session_id(mock_user_context: Any) -> None:
    mcp = SandboxMCP()
    # Type ignore because we are intentionally passing None to test runtime safety
    with pytest.raises(ValueError, match="Session ID is required"):
        await mcp.execute_code(None, "python", "print(1)", mock_user_context)  # type: ignore

    with pytest.raises(ValueError, match="Session ID is required"):
        await mcp.install_package(None, "pandas", mock_user_context)  # type: ignore

    with pytest.raises(ValueError, match="Session ID is required"):
        await mcp.list_files(None, mock_user_context, ".")  # type: ignore


@pytest.mark.asyncio
async def test_mcp_validation_whitespace_session_id(
    mock_factory: Any, mock_runtime: Any, mock_user_context: Any
) -> None:
    """Ensure whitespace strings are technically accepted by the validation check (truthy),
    but we want to ensure the system handles them as keys without crashing."""
    mcp = SandboxMCP()
    session_id = "   "

    await mcp.execute_code(session_id, "python", "pass", mock_user_context)
    assert session_id in mcp.sessions
    mock_runtime.execute.assert_called_once()

    await mcp.shutdown()


@pytest.mark.asyncio
async def test_mcp_validation_long_session_id(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """Ensure very long session IDs are handled correctly."""
    mcp = SandboxMCP()
    session_id = "a" * 1024

    await mcp.execute_code(session_id, "python", "pass", mock_user_context)
    assert session_id in mcp.sessions

    await mcp.shutdown()
