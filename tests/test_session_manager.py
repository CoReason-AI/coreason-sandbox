# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.session_manager import SessionManager


@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    runtime.terminate = AsyncMock()
    return runtime


@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.session_manager.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.mark.asyncio
async def test_session_creation(mock_factory: Any, mock_runtime: Any) -> None:
    manager = SessionManager()
    session_id = "test_session"

    session = await manager.get_or_create_session(session_id)

    assert session.runtime == mock_runtime
    mock_runtime.start.assert_called_once()
    assert session_id in manager.sessions


@pytest.mark.asyncio
async def test_session_creation_invalid_id() -> None:
    manager = SessionManager()
    with pytest.raises(ValueError, match="Session ID is required"):
        await manager.get_or_create_session("")


@pytest.mark.asyncio
async def test_session_reuse(mock_factory: Any, mock_runtime: Any) -> None:
    manager = SessionManager()
    session_id = "test_session"

    # Create first time
    session1 = await manager.get_or_create_session(session_id)

    # Create second time
    session2 = await manager.get_or_create_session(session_id)

    assert session1 is session2
    mock_runtime.start.assert_called_once()  # Should only be called once


@pytest.mark.asyncio
async def test_reaper_loop(mock_factory: Any, mock_runtime: Any) -> None:
    # Config: Check every 0.01s, expire after 100s
    config = SandboxConfig(idle_timeout=100.0, reaper_interval=0.01)
    manager = SessionManager(config)

    # Start time
    start_time = 1000.0

    with patch("coreason_sandbox.session_manager.time.time", return_value=start_time):
        await manager.get_or_create_session("expired_session")

    assert "expired_session" in manager.sessions

    # Advance time beyond timeout (1000 + 100 + 1)
    future_time = start_time + 150.0

    with patch("coreason_sandbox.session_manager.time.time", return_value=future_time):
        # Wait for reaper to cycle
        await asyncio.sleep(0.05)

        # Session should be gone
        assert "expired_session" not in manager.sessions
        mock_runtime.terminate.assert_called_once()

    await manager.shutdown()


@pytest.mark.asyncio
async def test_reaper_loop_exception_handling(mock_factory: Any, mock_runtime: Any) -> None:
    """Test that reaper loop survives exceptions during session termination."""
    config = SandboxConfig(idle_timeout=0.1, reaper_interval=0.01)
    manager = SessionManager(config)

    # Setup a session that throws on terminate
    mock_runtime.terminate.side_effect = Exception("Terminate failed")

    with patch("coreason_sandbox.session_manager.time.time", return_value=1000.0):
        await manager.get_or_create_session("fail_session")

    # Advance time to expire it
    with patch("coreason_sandbox.session_manager.time.time", return_value=1100.0):
        await asyncio.sleep(0.05)

    # Session should still be removed from dict even if terminate failed
    assert "fail_session" not in manager.sessions
    mock_runtime.terminate.assert_called_once()

    # Reaper should still be running (not crashed)
    assert manager._reaper_task is not None
    assert not manager._reaper_task.done()

    await manager.shutdown()


@pytest.mark.asyncio
async def test_reaper_loop_crash_recovery() -> None:
    """
    Test that if reaper loop logic itself crashes (top level), it is handled.
    (Though strictly speaking the try/except block inside loop handles specific logic errors,
    an exception outside the while loop or critical failure might be hard to test without injecting into the method)

    We can mock asyncio.sleep to raise an exception once?
    """
    manager = SessionManager(SandboxConfig(reaper_interval=0.01))

    # We want to verify the 'except Exception' block in _reaper_loop
    # We can mock asyncio.sleep to raise Exception
    with patch("asyncio.sleep", side_effect=[Exception("Crash"), asyncio.CancelledError()]):
        # Start reaper manually to await it
        await manager._reaper_loop()

    # The loop should have caught "Crash" and logged it, then caught CancelledError and exited.


@pytest.mark.asyncio
async def test_shutdown(mock_factory: Any, mock_runtime: Any) -> None:
    manager = SessionManager()
    await manager.get_or_create_session("s1")
    await manager.get_or_create_session("s2")

    assert len(manager.sessions) == 2
    assert manager._reaper_task is not None

    await manager.shutdown()

    assert len(manager.sessions) == 0
    assert mock_runtime.terminate.call_count == 2
    assert manager._reaper_task is None


@pytest.mark.asyncio
async def test_shutdown_with_error(mock_factory: Any, mock_runtime: Any) -> None:
    manager = SessionManager()
    await manager.get_or_create_session("s1")
    mock_runtime.terminate.side_effect = Exception("Fail")

    await manager.shutdown()

    assert len(manager.sessions) == 0
    # Should not raise
