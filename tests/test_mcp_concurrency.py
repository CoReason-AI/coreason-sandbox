import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from coreason_sandbox.mcp import SandboxMCP, Session
from coreason_sandbox.models import ExecutionResult


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
    with patch("coreason_sandbox.mcp.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.mark.asyncio
async def test_concurrent_session_creation(mock_factory: Any, mock_runtime: Any) -> None:
    """Verify concurrent creation creates only one runtime."""
    mcp = SandboxMCP()
    session_id = "concurrent_create"

    async def slow_start() -> None:
        await asyncio.sleep(0.05)

    mock_runtime.start.side_effect = slow_start

    t1 = asyncio.create_task(mcp._get_or_create_session(session_id))
    t2 = asyncio.create_task(mcp._get_or_create_session(session_id))

    s1, s2 = await asyncio.gather(t1, t2)

    assert s1 is s2
    mock_factory.assert_called_once()
    mock_runtime.start.assert_called_once()

    await mcp.shutdown()


async def _run_race_test(
    mcp: SandboxMCP, session_id: str, coro_func: Any, mock_runtime: Any, success_check: Any
) -> None:
    """Helper to run the race condition test pattern."""
    session1 = await mcp._get_or_create_session(session_id)
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

    session2 = Session(runtime=mock_runtime2, last_accessed=0)

    with patch.object(mcp, "_get_or_create_session", side_effect=[session1, session2]):
        t_exec = asyncio.create_task(coro_func())
        await asyncio.sleep(0.01)
        session1.lock.release()
        result = await t_exec

        success_check(result, mock_runtime, mock_runtime2)


@pytest.mark.asyncio
async def test_execution_during_reaping_race(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()

    def check(result: Any, r1: Any, r2: Any) -> None:
        assert result["stdout"] == "retry_success"
        r1.execute.assert_not_called()
        r2.execute.assert_called_once()

    await _run_race_test(mcp, "race_exec", lambda: mcp.execute_code("race_exec", "python", "pass"), mock_runtime, check)
    await mcp.shutdown()


@pytest.mark.asyncio
async def test_install_package_during_reaping_race(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()

    def check(result: Any, r1: Any, r2: Any) -> None:
        assert "installed successfully" in result
        r1.install_package.assert_not_called()
        r2.install_package.assert_called_once()

    await _run_race_test(mcp, "race_install", lambda: mcp.install_package("race_install", "pkg"), mock_runtime, check)
    await mcp.shutdown()


@pytest.mark.asyncio
async def test_list_files_during_reaping_race(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()

    def check(result: Any, r1: Any, r2: Any) -> None:
        assert result == ["retry_file"]
        r1.list_files.assert_not_called()
        r2.list_files.assert_called_once()

    await _run_race_test(mcp, "race_ls", lambda: mcp.list_files("race_ls", "."), mock_runtime, check)
    await mcp.shutdown()
