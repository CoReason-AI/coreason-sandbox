import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from coreason_sandbox.mcp import SandboxMCP


@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    runtime.terminate = AsyncMock()
    # Ensure execute returns something valid if called
    runtime.execute.return_value.artifacts = []
    return runtime


@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.mcp.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.mark.asyncio
async def test_reaper_exception_handling(mock_factory: Any, mock_runtime: Any) -> None:
    """Test that reaper handles unexpected exceptions (crashes) by logging and stopping."""
    mcp = SandboxMCP()

    # Patch sleep to raise Exception immediately
    with patch("coreason_sandbox.mcp.asyncio.sleep", side_effect=Exception("Crash")):
        await mcp._start_reaper_if_needed()
        assert mcp._reaper_task is not None
        await mcp._reaper_task
        assert mcp._reaper_task.done()


@pytest.mark.asyncio
async def test_reaper_cancellation_coverage(mock_factory: Any, mock_runtime: Any) -> None:
    """Test that reaper handles cancellation gracefully (lines 60-61)."""
    mcp = SandboxMCP()

    await mcp._start_reaper_if_needed()
    assert mcp._reaper_task is not None

    # Allow loop to start and enter sleep
    await asyncio.sleep(0.1)

    mcp._reaper_task.cancel()
    try:
        await mcp._reaper_task
    except asyncio.CancelledError:
        pass

    assert mcp._reaper_task.done()

    # Yield control to ensure async cleanup happens and coverage is flushed
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_shutdown_terminate_exception(mock_factory: Any, mock_runtime: Any) -> None:
    """Test that shutdown handles exceptions during runtime termination (lines 170-171)."""
    mcp = SandboxMCP()

    # Create a session
    await mcp._get_or_create_session("sess_fail")
    assert "sess_fail" in mcp.sessions

    # Mock terminate to raise exception
    mock_runtime.terminate.side_effect = Exception("Terminator Failed")

    # Should not raise exception, but log it
    await mcp.shutdown()

    # Verify we tried to terminate
    mock_runtime.terminate.assert_called_once()
