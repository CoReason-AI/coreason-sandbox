import pytest
import docker
from coreason_sandbox.runtimes.docker import DockerRuntime
from coreason_sandbox.models import ExecutionResult

@pytest.mark.live
@pytest.mark.asyncio
async def test_docker_runtime_live_lifecycle() -> None:
    """
    Live integration test for DockerRuntime.
    Verifies: Start -> Execute -> Terminate on a REAL container.
    """
    # Use standard image available in CI/Dev environments
    runtime = DockerRuntime(image="python:3.12-slim", timeout=30.0)

    try:
        # 1. Start
        print("Starting container...")
        await runtime.start()
        assert runtime.container is not None

        # 2. Execute Python
        print("Executing Python code...")
        code = "print('Hello Live World')"
        result = await runtime.execute(code, "python")

        assert isinstance(result, ExecutionResult)
        assert result.exit_code == 0
        assert "Hello Live World" in result.stdout
        assert result.stderr == ""

        # 3. Execute Bash
        print("Executing Bash code...")
        code_bash = "echo 'Hello Bash'"
        result_bash = await runtime.execute(code_bash, "bash")
        assert result_bash.exit_code == 0
        assert "Hello Bash" in result_bash.stdout.strip()

    except docker.errors.APIError as e:
        # Check for the specific overlayfs error common in some CI/Sandboxes
        if "failed to mount" in str(e) and "overlay" in str(e):
            pytest.skip(f"Docker Daemon reachable but failed to mount filesystem (Environment Issue): {e}")
        else:
            raise
    finally:
        # 4. Terminate
        print("Terminating container...")
        await runtime.terminate()
