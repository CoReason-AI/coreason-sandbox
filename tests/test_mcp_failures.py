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

@pytest.fixture(autouse=True)
def mock_veritas() -> Any:
    """Mock VeritasIntegrator to prevent OTLP connection errors during tests."""
    with patch("coreason_sandbox.mcp.VeritasIntegrator") as mock:
        mock.return_value.log_pre_execution = AsyncMock()
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

    # Allow loop to start
    await asyncio.sleep(0.01)

    mcp._reaper_task.cancel()
    try:
        await mcp._reaper_task
    except asyncio.CancelledError:
        # Should typically be suppressed by the task wrapper if handled,
        # but if we await it directly, we might see it depending on python version/impl.
        # However, our code catches it.
        pass

    assert mcp._reaper_task.done()

@pytest.mark.asyncio
async def test_shutdown_terminate_exception(mock_factory: Any, mock_runtime: Any) -> None:
    """Test that shutdown handles exceptions during runtime termination (lines 170-171)."""
    mcp = SandboxMCP()

    # Create a session
    await mcp._get_or_create_session("sess_fail")

    # Mock terminate to raise exception
    mock_runtime.terminate.side_effect = Exception("Terminator Failed")

    # Should not raise exception
    await mcp.shutdown()

    # Verify we tried to terminate
    mock_runtime.terminate.assert_called_once()
