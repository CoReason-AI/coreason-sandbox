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
from coreason_identity.models import UserContext
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
async def test_session_creation(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    manager = SessionManager()
    session_id = "test_session"

    session = await manager.get_or_create_session(session_id, mock_user_context)

    assert session.runtime == mock_runtime
    mock_runtime.start.assert_called_once()
    assert session_id in manager.sessions
    assert session.owner_id == "test-user"


@pytest.mark.asyncio
async def test_session_creation_invalid_id(mock_user_context: Any) -> None:
    manager = SessionManager()
    with pytest.raises(ValueError, match="Session ID is required"):
        await manager.get_or_create_session("", mock_user_context)


@pytest.mark.asyncio
async def test_session_creation_invalid_context() -> None:
    manager = SessionManager()
    with pytest.raises(ValueError, match="UserContext is required"):
        await manager.get_or_create_session("sess", None)


@pytest.mark.asyncio
async def test_session_reuse(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    manager = SessionManager()
    session_id = "test_session"

    # Create first time
    session1 = await manager.get_or_create_session(session_id, mock_user_context)

    # Create second time
    session2 = await manager.get_or_create_session(session_id, mock_user_context)

    assert session1 is session2
    mock_runtime.start.assert_called_once()  # Should only be called once


@pytest.mark.asyncio
async def test_session_access_denied(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    manager = SessionManager()
    session_id = "test_session"

    # Create with user1
    await manager.get_or_create_session(session_id, mock_user_context)

    # Try access with user2
    other_context = UserContext(
        sub="other-user",
        email="other@example.com",
        permissions=[],
    )

    with pytest.raises(PermissionError, match="Session belongs to another user"):
        await manager.get_or_create_session(session_id, other_context)


@pytest.mark.asyncio
async def test_session_creation_race_condition_access_denied(
    mock_factory: Any, mock_runtime: Any, mock_user_context: Any
) -> None:
    """
    Test race condition where two users try to create the same session ID.
    User 1 gets the lock and creates it.
    User 2 waits for lock, then sees it created but with wrong owner.
    """
    manager = SessionManager()
    session_id = "race_session"

    # Define User 2 context
    user2_context = UserContext(
        sub="user2",
        email="user2@example.com",
        permissions=[],
    )

    # Mock runtime.start to sleep slightly
    async def slow_start() -> None:
        await asyncio.sleep(0.1)

    mock_runtime.start.side_effect = slow_start

    # Start both tasks roughly at same time
    task1 = asyncio.create_task(manager.get_or_create_session(session_id, mock_user_context))

    # Slight delay to ensure task1 enters first and grabs lock
    await asyncio.sleep(0.01)

    task2 = asyncio.create_task(manager.get_or_create_session(session_id, user2_context))

    # Wait for results
    await task1

    # Task 2 should raise PermissionError
    with pytest.raises(PermissionError, match="Session belongs to another user"):
        await task2


@pytest.mark.asyncio
async def test_session_creation_race_condition_access_allowed(
    mock_factory: Any, mock_runtime: Any, mock_user_context: Any
) -> None:
    """
    Test race condition where two requests with SAME user try to create session.
    User 1 creates. User 2 waits for lock, then sees it created and succeeds.
    """
    manager = SessionManager()
    session_id = "race_session_ok"

    # Mock runtime.start to sleep slightly
    async def slow_start() -> None:
        await asyncio.sleep(0.1)

    mock_runtime.start.side_effect = slow_start

    # Start both tasks roughly at same time
    task1 = asyncio.create_task(manager.get_or_create_session(session_id, mock_user_context))

    # Slight delay to ensure task1 enters first and grabs lock
    await asyncio.sleep(0.01)

    # Same user context
    task2 = asyncio.create_task(manager.get_or_create_session(session_id, mock_user_context))

    # Wait for results
    session1 = await task1
    session2 = await task2

    assert session1 is session2
    assert session1.owner_id == "test-user"
    mock_runtime.start.assert_called_once()


@pytest.mark.asyncio
async def test_reaper_loop(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    # Config: Check every 0.01s, expire after 100s
    config = SandboxConfig(idle_timeout=100.0, reaper_interval=0.01)
    manager = SessionManager(config)

    # Start time
    start_time = 1000.0

    with patch("coreason_sandbox.session_manager.time.time", return_value=start_time):
        await manager.get_or_create_session("expired_session", mock_user_context)

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
async def test_reaper_loop_exception_handling(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """Test that reaper loop survives exceptions during session termination."""
    config = SandboxConfig(idle_timeout=0.1, reaper_interval=0.01)
    manager = SessionManager(config)

    # Setup a session that throws on terminate
    mock_runtime.terminate.side_effect = Exception("Terminate failed")

    with patch("coreason_sandbox.session_manager.time.time", return_value=1000.0):
        await manager.get_or_create_session("fail_session", mock_user_context)

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
    """
    manager = SessionManager(SandboxConfig(reaper_interval=0.01))

    # We want to verify the 'except Exception' block in _reaper_loop
    # We can mock asyncio.sleep to raise Exception
    with patch("asyncio.sleep", side_effect=[Exception("Crash"), asyncio.CancelledError()]):
        # Start reaper manually to await it
        await manager._reaper_loop()

    # The loop should have caught "Crash" and logged it, then caught CancelledError and exited.


@pytest.mark.asyncio
async def test_shutdown(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    manager = SessionManager()
    await manager.get_or_create_session("s1", mock_user_context)
    await manager.get_or_create_session("s2", mock_user_context)

    assert len(manager.sessions) == 2
    assert manager._reaper_task is not None

    await manager.shutdown()

    assert len(manager.sessions) == 0
    assert mock_runtime.terminate.call_count == 2
    assert manager._reaper_task is None


@pytest.mark.asyncio
async def test_shutdown_with_error(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    manager = SessionManager()
    await manager.get_or_create_session("s1", mock_user_context)
    mock_runtime.terminate.side_effect = Exception("Fail")

    await manager.shutdown()

    assert len(manager.sessions) == 0
    # Should not raise


@pytest.mark.asyncio
async def test_runtime_start_failure(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """Verify that if runtime.start() fails, the session is not cached."""
    manager = SessionManager()
    mock_runtime.start.side_effect = Exception("Start failed")

    with pytest.raises(Exception, match="Start failed"):
        await manager.get_or_create_session("fail_start", mock_user_context)

    # Session should not be in the dictionary
    assert "fail_start" not in manager.sessions

    # Subsequent success should work
    mock_runtime.start.side_effect = None
    session = await manager.get_or_create_session("fail_start", mock_user_context)
    assert session is not None
    assert "fail_start" in manager.sessions


@pytest.mark.asyncio
async def test_zero_idle_timeout(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """Verify behavior when idle_timeout is 0 (immediate expiration)."""
    # Config: 0 timeout
    config = SandboxConfig(idle_timeout=0.0, reaper_interval=0.01)
    manager = SessionManager(config)

    # Use real time mostly, but patch for control if needed
    # If we insert a session, it is immediately expired.

    with patch("coreason_sandbox.session_manager.time.time", return_value=1000.0):
        await manager.get_or_create_session("immediate_expire", mock_user_context)

    assert "immediate_expire" in manager.sessions

    # Advance time by minimal amount (e.g. 0.0001) which is > 0.0
    with patch("coreason_sandbox.session_manager.time.time", return_value=1000.0001):
        await asyncio.sleep(0.05)  # Wait for reaper

        assert "immediate_expire" not in manager.sessions
        mock_runtime.terminate.assert_called_once()

    await manager.shutdown()
