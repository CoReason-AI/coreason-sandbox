import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.mcp import SandboxMCP
from docker.errors import DockerException


@pytest.mark.asyncio
async def test_stress_mixed_workload(mock_user_context: Any) -> None:
    """
    Simulates a mixed workload with:
    1. Successful Python executions
    2. Bash executions
    3. Docker runtime failures (simulated)
    4. Session reuse vs new session creation
    """
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock_docker_cls:
        # Setup Mock
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_docker_cls.return_value = mock_client
        mock_client.containers.run.return_value = mock_container
        mock_container.short_id = "stress-complex"

        # Dynamic side effect for exec_run
        # Returns success, stderr, or raises DockerException based on command content
        def mock_exec_run(*args: Any, **kwargs: Any) -> tuple[int, bytes | tuple[bytes, bytes]]:
            cmd_args = args[0] if args else kwargs.get("cmd", "")
            cmd_str = str(cmd_args)

            if "ls -1" in cmd_str:
                # list_files (demux=False)
                return (0, b"file1.txt")

            # Simulate random failure based on code content injected by test
            if "FORCE_FAILURE" in cmd_str:
                raise DockerException("Simulated Docker Crash")

            if "FORCE_ERROR" in cmd_str:
                # demux=True -> (stdout, stderr)
                return (1, (b"", b"Syntax Error"))

            # Success
            return (0, (b"Success", b""))

        mock_container.exec_run.side_effect = mock_exec_run

        config = SandboxConfig(
            runtime="docker",
            execution_timeout=5.0,
            idle_timeout=60.0,
            enable_audit_logging=False,
        )
        mcp = SandboxMCP(config)

        CONCURRENCY = 30

        async def worker(i: int) -> str:
            # reuse sessions for evens, new for odds
            session_id = f"session-{i % 5}"

            behavior = i % 3
            if behavior == 0:
                code = "print('OK')"
            elif behavior == 1:
                code = "FORCE_ERROR"
            else:
                code = "FORCE_FAILURE"

            try:
                res = await mcp.execute_code(session_id, "python", code, mock_user_context)
                if behavior == 0:
                    assert res["exit_code"] == 0
                elif behavior == 1:
                    assert res["exit_code"] == 1
                return "handled"
            except Exception as e:
                # For FORCE_FAILURE, execute_code catches DockerException?
                # No, SandboxMCP.execute_code -> runtime.execute -> calls docker.
                # If runtime raises DockerException, SandboxMCP propagates it?
                # Let's check SandboxMCP code. It catches generic Exception in main.py wrapper,
                # but SandboxMCP.execute_code itself propagates?
                # Wait, test_mcp.py shows it propagates.
                return f"exception: {e}"

        tasks = [worker(i) for i in range(CONCURRENCY)]
        results = await asyncio.gather(*tasks)

        # Verify robustness
        exceptions = [r for r in results if "exception" in r]
        successes = [r for r in results if r == "handled"]

        # We expect roughly 1/3 exceptions (FORCE_FAILURE)
        assert len(exceptions) > 0
        assert len(successes) > 0

        # Verify Session Manager is still alive
        assert len(mcp.sessions) <= 5  # We used modulo 5 for IDs

        await mcp.shutdown()


@pytest.mark.asyncio
async def test_stress_reaper_collision(mock_user_context: Any) -> None:
    """
    Simulates concurrent access while the reaper is removing idle sessions.
    """
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock_docker_cls:
        # Minimal mock
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_docker_cls.return_value = mock_client
        mock_client.containers.run.return_value = mock_container

        # exec_run must return tuple
        mock_container.exec_run.return_value = (0, (b"OK", b""))

        # Config with very short idle timeout to trigger reaping
        config = SandboxConfig(
            runtime="docker",
            idle_timeout=0.1,  # expire quickly
            reaper_interval=0.1,  # check quickly
            enable_audit_logging=False,
        )
        mcp = SandboxMCP(config)

        # 1. Create a session
        await mcp.execute_code("session-reap", "python", "print('init')", mock_user_context)

        # 2. Wait for it to expire (sleep > idle_timeout)
        await asyncio.sleep(0.2)

        # 3. Try to access it concurrent with reaper
        # To strictly test collision, we'd need to control the reaper task execution,
        # but with short intervals, we rely on probability in this stress test.
        # We will spam requests to see if we hit a "Session active=False" or lock issue.

        async def spammer() -> str:
            try:
                # get_or_create should resurrect the session if it was reaped
                await mcp.execute_code("session-reap", "python", "print('spam')", mock_user_context)
                return "ok"
            except Exception as e:
                return f"error: {e}"

        results = await asyncio.gather(*(spammer() for _ in range(10)))

        # All should ideally succeed by creating new sessions if old was reaped
        errors = [r for r in results if "error" in r]
        assert not errors, f"Encountered errors during reaper collision: {errors}"

        await mcp.shutdown()
