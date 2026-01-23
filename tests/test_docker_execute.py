import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.runtimes.docker import DockerRuntime


@pytest.fixture
def mock_docker_client() -> Any:
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock:
        yield mock


@pytest.fixture
def docker_runtime(mock_docker_client: Any) -> Any:
    runtime = DockerRuntime()
    # Mock a started container
    runtime.container = MagicMock()
    runtime.container.short_id = "test_id"
    return runtime


@pytest.mark.asyncio
async def test_execute_python_success(docker_runtime: Any) -> None:
    # Setup mock return for exec_run sequence:
    # 1. ls (before)
    # 2. python code
    # 3. ls (after)
    docker_runtime.container.exec_run.side_effect = [
        (0, b""),  # ls before
        (0, (b"hello\n", b"")),  # python execution
        (0, b""),  # ls after
    ]

    # Mock time.time() to ensure non-zero duration
    with patch("coreason_sandbox.runtimes.docker.time.time", side_effect=[1000.0, 1001.5]):
        result = await docker_runtime.execute("print('hello')", "python")

    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0
    assert result.stdout == "hello\n"
    assert result.stderr == ""
    assert result.execution_duration == 1.5

    # Verify calls
    assert docker_runtime.container.exec_run.call_count == 3
    # 2nd call should be the code execution
    args, kwargs = docker_runtime.container.exec_run.call_args_list[1]
    assert args[0] == ["python", "-c", "print('hello')"]
    assert kwargs["demux"] is True


@pytest.mark.asyncio
async def test_execute_bash_success(docker_runtime: Any) -> None:
    docker_runtime.container.exec_run.side_effect = [(0, b""), (0, (b"root\n", b"")), (0, b"")]

    result = await docker_runtime.execute("whoami", "bash")

    assert result.stdout == "root\n"
    args, _ = docker_runtime.container.exec_run.call_args_list[1]
    assert args[0] == ["bash", "-c", "whoami"]


@pytest.mark.asyncio
async def test_execute_stderr(docker_runtime: Any) -> None:
    docker_runtime.container.exec_run.side_effect = [(0, b""), (1, (b"", b"error details")), (0, b"")]

    result = await docker_runtime.execute("invalid", "bash")

    assert result.exit_code == 1
    assert result.stderr == "error details"
    assert result.stdout == ""


@pytest.mark.asyncio
async def test_execute_no_container(mock_docker_client: Any) -> None:
    # Runtime without start() called
    runtime = DockerRuntime()
    with pytest.raises(RuntimeError, match="Sandbox not started"):
        await runtime.execute("print(1)", "python")


@pytest.mark.asyncio
async def test_execute_unsupported_language(docker_runtime: Any) -> None:
    # `execute` calls `_list_files_internal` first, so we need to mock that or let it run
    # Mocking ls to succeed
    docker_runtime.container.exec_run.return_value = (0, b"")

    with pytest.raises(ValueError, match="Unsupported language"):
        await docker_runtime.execute("code", "java")


@pytest.mark.asyncio
async def test_execute_r_language(docker_runtime: Any) -> None:
    docker_runtime.container.exec_run.side_effect = [(0, b""), (0, (b"[1] 4\n", b"")), (0, b"")]

    result = await docker_runtime.execute("2+2", "r")

    assert result.stdout == "[1] 4\n"
    args, _ = docker_runtime.container.exec_run.call_args_list[1]
    assert args[0] == ["Rscript", "-e", "2+2"]


@pytest.mark.asyncio
async def test_execute_exception(docker_runtime: Any) -> None:
    from docker.errors import DockerException

    # Fail on execution step
    docker_runtime.container.exec_run.side_effect = [(0, b""), DockerException("Fail")]

    with pytest.raises(DockerException):
        await docker_runtime.execute("code", "python")


@pytest.mark.asyncio
async def test_execute_artifact_handling_failure(docker_runtime: Any) -> None:
    # Simulate success execution but failure in artifact retrieval
    docker_runtime.container.exec_run.side_effect = [
        (0, b""),  # Before ls
        (0, (b"", b"")),  # Exec
        (0, b"new_file\n"),  # After ls
    ]

    # Mock download to fail
    # Use patch to mock the download method on the instance
    with patch.object(docker_runtime, "download", side_effect=Exception("Download failed")):
        result = await docker_runtime.execute("code", "python")

        assert result.exit_code == 0
        # Artifacts should be empty because download failed
        assert len(result.artifacts) == 0


@pytest.mark.asyncio
async def test_execute_timeout(docker_runtime: Any) -> None:
    # Test that execution times out after limit

    # Define a side effect that sleeps to simulate long execution
    # Since we are using asyncio.to_thread, time.sleep works (it blocks the thread)
    def blocking_exec(*args: Any, **kwargs: Any) -> tuple[int, tuple[bytes, bytes]]:
        time.sleep(0.5)
        return (0, (b"done", b""))

    # Mock wait_for to have a very short timeout so we don't actually wait 60s
    original_wait_for = asyncio.wait_for

    async def mock_wait_for(fut: Any, timeout: float) -> Any:
        # We ignore the requested timeout (60s) and use a very short one (0.1s)
        # effectively simulating that the task took too long relative to the limit
        return await original_wait_for(fut, timeout=0.1)

    # Prepare mocks
    docker_runtime.container.exec_run.side_effect = blocking_exec

    call_count = 0

    def side_effect(*args: Any, **kwargs: Any) -> tuple[int, bytes | tuple[bytes, bytes]]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # ls before
            return (0, b"")
        if call_count == 2:  # exec code
            time.sleep(0.5)  # Blocks for 0.5s
            return (0, (b"done", b""))
        return (0, b"")

    docker_runtime.container.exec_run.side_effect = side_effect

    with patch("asyncio.wait_for", side_effect=mock_wait_for):
        with pytest.raises(TimeoutError, match="Execution exceeded"):
            await docker_runtime.execute("while True: pass", "python")

    # Verify restart was called
    docker_runtime.container.restart.assert_called_once()
