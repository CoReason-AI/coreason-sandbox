from pathlib import Path
from typing import AsyncGenerator

import docker
import pytest
from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.runtimes.docker import DockerRuntime


@pytest.fixture
async def live_docker_runtime() -> AsyncGenerator[DockerRuntime, None]:
    """
    Fixture to provide a started DockerRuntime for live tests.
    Handles environment checks and skips if Docker is unavailable.
    """
    runtime = None
    try:
        # Use standard image available in CI/Dev environments
        runtime = DockerRuntime(image="python:3.12-slim", timeout=30.0)
        print("Starting container...")
        await runtime.start()
        yield runtime
    except docker.errors.ImageNotFound as e:
        pytest.skip(f"Docker image not found/pull failed (Environment Issue): {e}")
    except docker.errors.APIError as e:
        if "failed to mount" in str(e) and "overlay" in str(e):
            pytest.skip(f"Docker Daemon reachable but failed to mount filesystem (Environment Issue): {e}")
        else:
            raise
    except docker.errors.DockerException as e:
        if "Connection aborted" in str(e) or "FileNotFoundError" in str(e):
            pytest.skip(f"Docker connection lost/unreachable (Environment Issue): {e}")
        else:
            raise
    finally:
        if runtime:
            print("Terminating container...")
            await runtime.terminate()


@pytest.mark.live
@pytest.mark.asyncio
async def test_docker_runtime_live_lifecycle(live_docker_runtime: DockerRuntime) -> None:
    """
    Live integration test for DockerRuntime lifecycle.
    Verifies: Execute Python and Bash on a REAL container.
    """
    runtime = live_docker_runtime
    assert runtime.container is not None

    # 1. Execute Python
    print("Executing Python code...")
    code = "print('Hello Live World')"
    result = await runtime.execute(code, "python")

    assert isinstance(result, ExecutionResult)
    assert result.exit_code == 0
    assert "Hello Live World" in result.stdout
    assert result.stderr == ""

    # 2. Execute Bash
    print("Executing Bash code...")
    code_bash = "echo 'Hello Bash'"
    result_bash = await runtime.execute(code_bash, "bash")
    assert result_bash.exit_code == 0
    assert "Hello Bash" in result_bash.stdout.strip()


@pytest.mark.live
@pytest.mark.asyncio
async def test_docker_io_live(live_docker_runtime: DockerRuntime, tmp_path: Path) -> None:
    """
    Live integration test for File I/O.
    Verifies: Upload -> Execute (read/write) -> Download.
    """
    runtime = live_docker_runtime

    # 1. Prepare local file
    test_content = "Integration Test Content"
    local_file = tmp_path / "upload_test.txt"
    local_file.write_text(test_content)

    # 2. Upload
    remote_path = "/home/sandbox/uploaded.txt"
    await runtime.upload(local_file, remote_path)

    # Verify existence with bash
    ls_result = await runtime.execute(f"cat {remote_path}", "bash")
    assert ls_result.exit_code == 0
    assert ls_result.stdout.strip() == test_content

    # 3. Create file in container (via Python) and download
    code = """
with open('/home/sandbox/generated.txt', 'w') as f:
    f.write('Generated Content')
"""
    await runtime.execute(code, "python")

    download_path = tmp_path / "downloaded.txt"
    await runtime.download("/home/sandbox/generated.txt", download_path)

    assert download_path.exists()
    assert download_path.read_text() == "Generated Content"


@pytest.mark.live
@pytest.mark.asyncio
async def test_docker_isolation_live(live_docker_runtime: DockerRuntime) -> None:
    """
    Live integration test for concurrency/isolation.
    Starts a SECOND runtime to ensure it's distinct from the fixture's runtime.
    """
    runtime1 = live_docker_runtime

    # Start Runtime 2 manually (fixture pattern implies single instance per test usually,
    # but we can instantiate another for this specific test)
    # Reuse logic? We'll just instantiate directly.
    runtime2 = DockerRuntime(image="python:3.12-slim", timeout=30.0)

    try:
        await runtime2.start()

        # Verify different containers
        assert runtime1.container is not None
        assert runtime2.container is not None
        assert runtime1.container.id != runtime2.container.id

        # Write to Runtime 1
        await runtime1.execute("touch /home/sandbox/unique_file", "bash")

        # Check Runtime 2 (should not have file)
        result = await runtime2.execute("ls /home/sandbox/unique_file", "bash")
        assert result.exit_code != 0  # Should fail

    except (docker.errors.DockerException, docker.errors.APIError) as e:
        # If runtime2 fails to start due to env, we can't test isolation fully, but runtime1 succeeded (fixture).
        # We might skip here if it's an overlayfs error etc.
        pytest.skip(f"Second container failed (Environment Issue): {e}")
    finally:
        await runtime2.terminate()
