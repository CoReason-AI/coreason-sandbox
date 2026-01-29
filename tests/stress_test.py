import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.mcp import SandboxMCP


@pytest.mark.asyncio
async def test_stress_concurrency(mock_user_context: Any) -> None:
    """
    Stress test to verify SessionManager and DockerRuntime stability under high load.
    Simulates 50 concurrent sessions using a mocked Docker backend to test
    asyncio locking, session creation, and deadlock prevention.
    """
    # 1. Setup Mock Docker Environment
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock_docker_cls:
        # Configure Mock Client and Container
        mock_client = MagicMock()
        mock_container = MagicMock()

        mock_docker_cls.return_value = mock_client
        mock_client.containers.run.return_value = mock_container

        # Configure container attributes
        mock_container.short_id = "mock-cnt-123"

        # Configure exec_run to simulate work without blocking
        # NOTE: DockerRuntime uses demux=True, so return (exit_code, (stdout, stderr))
        def mock_exec_run(*args: Any, **kwargs: Any) -> tuple[int, bytes | tuple[bytes, bytes]]:
            # Check if ls -1 is called
            cmd_args = args[0] if args else kwargs.get("cmd", "")
            cmd_str = str(cmd_args)

            if "ls -1" in cmd_str:
                # ls usually returns (exit, output_bytes) if demux=False?
                # DockerRuntime calls: self.container.exec_run(f"ls -1 {path}") -> Default demux=False?
                # Let's check source code.
                # runtime.py: list_files: exit_code, output = self.container.exec_run(f"ls -1 {path}")
                # It does NOT use demux=True for list_files.
                return (0, b"file1.txt\nfile2.txt")
            else:
                # execute() uses demux=True
                # exit_code, output = ... exec_run(..., demux=True)
                # If demux=True, output is (stdout, stderr)
                time.sleep(0.01)  # Simulate execution
                return (0, (b"Result\n", b""))

        mock_container.exec_run.side_effect = mock_exec_run

        # 2. Initialize MCP
        # Disable audit logging to prevent OTLP connection errors
        config = SandboxConfig(
            runtime="docker",
            execution_timeout=5.0,
            idle_timeout=60.0,
            enable_audit_logging=False,
        )
        mcp = SandboxMCP(config)

        # 3. Define Workload
        CONCURRENCY = 50

        async def worker(i: int) -> dict[str, str | int | float | list[dict[str, Any]]]:
            session_id = f"stress-session-{i}"
            code = f"print('Hello from {i}')"

            # Execute code
            result = await mcp.execute_code(session_id, "python", code, mock_user_context)

            return result

        # 4. Execute Concurrent Load
        start_time = time.time()
        tasks = [worker(i) for i in range(CONCURRENCY)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # 5. Assertions
        assert len(results) == CONCURRENCY

        # Verify all succeeded
        for res in results:
            # result is dict
            assert res["exit_code"] == 0
            # Check stdout in the returned dictionary
            # The mocked stdout is b"Result\n" which decodes to "Result\n"
            assert "Result" in str(res.get("stdout"))

        # Verify Session Manager State
        # Should have CONCURRENCY sessions created
        assert len(mcp.sessions) == CONCURRENCY

        print(f"Completed {CONCURRENCY} concurrent sessions in {duration:.2f}s")

        # Cleanup
        await mcp.shutdown()
