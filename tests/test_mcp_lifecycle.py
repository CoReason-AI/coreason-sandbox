import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.mcp import SandboxMCP
from coreason_sandbox.models import ExecutionResult


@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    runtime.terminate = AsyncMock()
    # Return valid ExecutionResult
    result = ExecutionResult(stdout="", stderr="", exit_code=0, artifacts=[], execution_duration=0.1)
    runtime.execute.return_value = result
    return runtime


@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.session_manager.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_veritas() -> Any:
    """Mock VeritasIntegrator to prevent OTLP connection errors during tests."""
    with patch("coreason_sandbox.mcp.VeritasIntegrator") as mock:
        mock.return_value.log_pre_execution = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_session_creation_and_reuse(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    mcp = SandboxMCP()

    # 1. Create Session
    session_id = "sess_1"
    session1 = await mcp.session_manager.get_or_create_session(session_id, mock_user_context)
    assert session1.runtime == mock_runtime
    mock_runtime.start.assert_called_once()
    assert session_id in mcp.sessions

    # Capture timestamp
    ts1 = session1.last_accessed

    # 2. Reuse Session
    # Ensure time advances slightly
    with patch("coreason_sandbox.session_manager.time.time", return_value=ts1 + 10):
        session1_again = await mcp.session_manager.get_or_create_session(session_id, mock_user_context)
        assert session1_again is session1
        assert session1_again.last_accessed == ts1 + 10

    # Runtime start should NOT be called again
    mock_runtime.start.assert_called_once()

    await mcp.shutdown()


@pytest.mark.asyncio
async def test_reaper_terminates_expired_sessions(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    # Config: Check every 0.01s, expire after 100s
    config = SandboxConfig(idle_timeout=100.0, reaper_interval=0.01)
    mcp = SandboxMCP(config)

    # Start time
    start_time = 1000.0

    with patch("coreason_sandbox.session_manager.time.time", return_value=start_time):
        await mcp.session_manager.get_or_create_session("expired_session", mock_user_context)

    assert "expired_session" in mcp.sessions

    # Advance time beyond timeout (1000 + 100 + 1)
    future_time = start_time + 150.0

    with patch("coreason_sandbox.session_manager.time.time", return_value=future_time):
        # Wait for reaper to cycle
        await asyncio.sleep(0.05)

        # Session should be gone
        assert "expired_session" not in mcp.sessions
        mock_runtime.terminate.assert_called_once()

    await mcp.shutdown()


@pytest.mark.asyncio
async def test_reaper_ignores_active_sessions(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    # Config: Check every 0.01s, expire after 100s
    config = SandboxConfig(idle_timeout=100.0, reaper_interval=0.01)
    mcp = SandboxMCP(config)

    start_time = 1000.0

    with patch("coreason_sandbox.session_manager.time.time", return_value=start_time):
        await mcp.session_manager.get_or_create_session("active_session", mock_user_context)

    # Advance time within timeout (1000 + 50)
    future_time = start_time + 50.0

    with patch("coreason_sandbox.session_manager.time.time", return_value=future_time):
        await asyncio.sleep(0.05)

        # Should still be there
        assert "active_session" in mcp.sessions
        mock_runtime.terminate.assert_not_called()

    await mcp.shutdown()


@pytest.mark.asyncio
async def test_shutdown_cleans_up(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    mcp = SandboxMCP()
    await mcp.session_manager.get_or_create_session("s1", mock_user_context)
    await mcp.session_manager.get_or_create_session("s2", mock_user_context)

    assert len(mcp.sessions) == 2
    assert mcp._reaper_task is not None

    await mcp.shutdown()

    assert len(mcp.sessions) == 0
    assert mock_runtime.terminate.call_count == 2
    assert mcp._reaper_task is None


@pytest.mark.asyncio
async def test_concurrent_access_sequentiality(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """Ensure session lock prevents concurrent execution on the same session."""
    mcp = SandboxMCP()
    session_id = "sess_lock"

    # Mock execute to be slow
    async def slow_execute(*args: Any, **kwargs: Any) -> ExecutionResult:
        await asyncio.sleep(0.05)
        return ExecutionResult(stdout="", stderr="", exit_code=0, artifacts=[], execution_duration=0.05)

    mock_runtime.execute.side_effect = slow_execute

    # Start two executions concurrently
    t1 = asyncio.create_task(mcp.execute_code(session_id, "python", "1", mock_user_context))
    t2 = asyncio.create_task(mcp.execute_code(session_id, "python", "2", mock_user_context))

    start = time.time()
    await asyncio.gather(t1, t2)
    end = time.time()

    # If parallel, takes ~0.05s. If sequential, takes ~0.1s.
    # Note: local test execution time might vary, but logic holds.
    # Since we are using asyncio.sleep in mock, the event loop effectively serializes them
    # if the lock is held.
    # With lock:
    # t1 acquires lock, sleeps 0.05.
    # t2 waits for lock.
    # t1 releases. t2 acquires, sleeps 0.05.
    # Total ~0.1s.

    # Allow slight variance (e.g., 0.09s) due to loop overhead/clock resolution
    assert (end - start) >= 0.08

    await mcp.shutdown()
