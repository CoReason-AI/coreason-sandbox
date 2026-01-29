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
from coreason_sandbox.mcp import SandboxMCP
from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.session_manager import Session


@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    runtime.terminate = AsyncMock()
    runtime.execute.return_value = ExecutionResult(
        stdout="done", stderr="", exit_code=0, artifacts=[], execution_duration=0.1
    )
    runtime.list_files.return_value = ["file1"]
    return runtime


@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.session_manager.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.mark.asyncio
async def test_concurrent_session_creation(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """Verify concurrent creation creates only one runtime."""
    mcp = SandboxMCP()
    session_id = "concurrent_create"

    async def slow_start() -> None:
        await asyncio.sleep(0.05)

    mock_runtime.start.side_effect = slow_start

    # Access session_manager directly
    t1 = asyncio.create_task(mcp.session_manager.get_or_create_session(session_id, mock_user_context))
    t2 = asyncio.create_task(mcp.session_manager.get_or_create_session(session_id, mock_user_context))

    s1, s2 = await asyncio.gather(t1, t2)

    assert s1 is s2
    mock_factory.assert_called_once()
    mock_runtime.start.assert_called_once()

    await mcp.shutdown()


async def _run_race_test(
    mcp: SandboxMCP,
    session_id: str,
    coro_func: Any,
    mock_runtime: Any,
    success_check: Any,
    mock_user_context: Any,
) -> None:
    """Helper to run the race condition test pattern."""
    session1 = await mcp.session_manager.get_or_create_session(session_id, mock_user_context)
    await session1.lock.acquire()

    # Simulate session 1 poisoned
    session1.active = False

    # Mock runtime for session 2
    mock_runtime2 = AsyncMock()
    mock_runtime2.start = AsyncMock()
    # Setup returns
    mock_runtime2.execute.return_value = ExecutionResult(
        stdout="retry_success", stderr="", exit_code=0, artifacts=[], execution_duration=0.1
    )
    mock_runtime2.list_files.return_value = ["retry_file"]

    session2 = Session(runtime=mock_runtime2, last_accessed=0, owner_id=mock_user_context.user_id)

    # Patch the method on the session_manager instance
    with patch.object(mcp.session_manager, "get_or_create_session", side_effect=[session1, session2]):
        t_exec = asyncio.create_task(coro_func())
        await asyncio.sleep(0.01)
        session1.lock.release()
        result = await t_exec

        success_check(result, mock_runtime, mock_runtime2)


@pytest.mark.asyncio
async def test_execution_during_reaping_race(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    mcp = SandboxMCP()

    def check(result: Any, r1: Any, r2: Any) -> None:
        assert result["stdout"] == "retry_success"
        r1.execute.assert_not_called()
        r2.execute.assert_called_once()

    await _run_race_test(
        mcp,
        "race_exec",
        lambda: mcp.execute_code("race_exec", "python", "pass", mock_user_context),
        mock_runtime,
        check,
        mock_user_context,
    )
    await mcp.shutdown()


@pytest.mark.asyncio
async def test_install_package_during_reaping_race(
    mock_factory: Any, mock_runtime: Any, mock_user_context: Any
) -> None:
    mcp = SandboxMCP()

    def check(result: Any, r1: Any, r2: Any) -> None:
        assert "installed successfully" in result
        r1.install_package.assert_not_called()
        r2.install_package.assert_called_once()

    await _run_race_test(
        mcp,
        "race_install",
        lambda: mcp.install_package("race_install", "pkg", mock_user_context),
        mock_runtime,
        check,
        mock_user_context,
    )
    await mcp.shutdown()


@pytest.mark.asyncio
async def test_list_files_during_reaping_race(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    mcp = SandboxMCP()

    def check(result: Any, r1: Any, r2: Any) -> None:
        assert result == ["retry_file"]
        r1.list_files.assert_not_called()
        r2.list_files.assert_called_once()

    await _run_race_test(
        mcp,
        "race_ls",
        lambda: mcp.list_files("race_ls", mock_user_context, "."),
        mock_runtime,
        check,
        mock_user_context,
    )
    await mcp.shutdown()


@pytest.mark.asyncio
async def test_thundering_herd_on_dying_session(mock_factory: Any, mock_runtime: Any, mock_user_context: Any) -> None:
    """
    Simulate multiple concurrent requests accessing a session that is being reaped.
    All should eventually succeed with a valid (new) session.
    """
    mcp = SandboxMCP()
    session_id = "thundering_herd"

    # 1. Setup initial session
    session1 = await mcp.session_manager.get_or_create_session(session_id, mock_user_context)

    # Simulate session1 is being reaped (active=False) but lock held by reaper (simulated by us acquiring it)
    await session1.lock.acquire()
    session1.active = False

    # 2. Setup replacement session
    mock_runtime2 = AsyncMock()
    mock_runtime2.start = AsyncMock()
    mock_runtime2.execute.return_value = ExecutionResult(
        stdout="herd_success", stderr="", exit_code=0, artifacts=[], execution_duration=0.1
    )
    session2 = Session(runtime=mock_runtime2, last_accessed=0, owner_id=mock_user_context.user_id)

    # 3. Patch get_or_create_session to return session1 (doomed) first for ALL concurrent calls,
    #    then session2 for the retry.
    #    Since multiple calls will retry, we need session2 to be returned multiple times or cached.
    #    Ideally, the first retry creates session2, subsequent retries get session2.

    call_count = 0
    num_requests = 5

    async def dynamic_side_effect(sid: str, ctx: Any) -> Session:
        nonlocal call_count
        call_count += 1
        # The first 'num_requests' calls get the doomed session
        if call_count <= num_requests:
            return session1
        return session2

    with patch.object(mcp.session_manager, "get_or_create_session", side_effect=dynamic_side_effect):
        # Launch concurrent requests
        tasks = [
            asyncio.create_task(mcp.execute_code(session_id, "python", "pass", mock_user_context))
            for _ in range(num_requests)
        ]

        # Allow them to hit the lock
        await asyncio.sleep(0.01)

        # Release lock (simulate reaper finishing termination)
        session1.lock.release()

        results = await asyncio.gather(*tasks)

        # Verifications
        for res in results:
            assert res["stdout"] == "herd_success"

        # runtime1 should NOT be executed
        mock_runtime.execute.assert_not_called()

        # runtime2 should be executed 'num_requests' times
        assert mock_runtime2.execute.call_count == num_requests

    await mcp.shutdown()
