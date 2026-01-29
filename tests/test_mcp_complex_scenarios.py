import asyncio
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
async def test_complex_concurrent_mixed_validation(
    mock_factory: Any, mock_runtime: Any, mock_user_context: Any
) -> None:
    """
    Simulate concurrent requests where some have valid IDs and some have invalid (empty) IDs.
    Ensure that invalid requests are rejected immediately without affecting valid sessions.
    """
    mcp = SandboxMCP()
    valid_id = "valid_session"

    # Define tasks
    async def valid_req() -> str:
        res = await mcp.execute_code(valid_id, "python", "pass", mock_user_context)
        return str(res["stdout"])

    async def invalid_req() -> None:
        await mcp.execute_code("", "python", "pass", mock_user_context)

    # Run concurrently
    # We expect valid_req to succeed and invalid_req to raise ValueError

    task_valid = asyncio.create_task(valid_req())

    with pytest.raises(ValueError, match="Session ID is required"):
        await invalid_req()

    await task_valid

    # Assert state
    assert valid_id in mcp.sessions
    assert len(mcp.sessions) == 1

    await mcp.shutdown()


@pytest.mark.asyncio
async def test_complex_rapid_lifecycle_mixed_ids(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """
    Simulate a client rapidly creating sessions, some with valid keys, some invalid.
    """
    mcp = SandboxMCP()

    ids = ["valid1", "", "valid2", None, "valid3"]

    results = []

    for sid in ids:
        try:
            # type check: ignore for None
            await mcp.execute_code(sid, "python", "pass", mock_user_context)  # type: ignore
            results.append((sid, "success"))
        except ValueError:
            results.append((sid, "error"))

    # verification
    assert results == [
        ("valid1", "success"),
        ("", "error"),
        ("valid2", "success"),
        (None, "error"),
        ("valid3", "success"),
    ]

    assert len(mcp.sessions) == 3
    assert "valid1" in mcp.sessions
    assert "valid2" in mcp.sessions
    assert "valid3" in mcp.sessions

    await mcp.shutdown()
