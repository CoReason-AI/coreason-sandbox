import os
from typing import AsyncGenerator

import docker
import pytest
import pytest_asyncio
from coreason_identity.models import UserContext
from coreason_sandbox.runtimes.docker import DockerRuntime


@pytest_asyncio.fixture(scope="module")
async def built_docker_image() -> AsyncGenerator[str, None]:
    """
    Builds the Docker image from the project Dockerfile for testing.
    Returns the image tag.
    """
    image_tag = "coreason-sandbox-test:latest"

    try:
        client = docker.from_env()
        # Build image
        # This assumes the test is run from the project root
        project_root = os.getcwd()
        print(f"Building Docker image from {project_root}...")
        client.images.build(path=project_root, dockerfile="Dockerfile", tag=image_tag, rm=True)
        yield image_tag
    except (docker.errors.BuildError, docker.errors.APIError, docker.errors.DockerException) as e:
        pytest.skip(f"Failed to build/connect Docker: {e}")
    finally:
        # Cleanup if needed (optional, keeping it cached is faster)
        pass


@pytest_asyncio.fixture
async def filesystem_docker_runtime(built_docker_image: str) -> AsyncGenerator[DockerRuntime, None]:
    runtime = None
    try:
        runtime = DockerRuntime(image=built_docker_image, timeout=30.0)
        await runtime.start()
        yield runtime
    except (docker.errors.ImageNotFound, docker.errors.DockerException, docker.errors.APIError) as e:
        pytest.skip(f"Docker environment issue: {e}")
    finally:
        if runtime:
            await runtime.terminate()


@pytest.mark.live
@pytest.mark.asyncio
async def test_verify_user_identity(filesystem_docker_runtime: DockerRuntime, mock_user_context: UserContext) -> None:
    """Verify the container is running as 'user' with the correct home."""
    runtime = filesystem_docker_runtime

    # 1. Check User
    res_user = await runtime.execute("whoami", "bash", mock_user_context, "sid")
    assert res_user.exit_code == 0
    assert res_user.stdout.strip() == "user"

    # 2. Check Home Env
    res_home = await runtime.execute("echo $HOME", "bash", mock_user_context, "sid")
    assert res_home.exit_code == 0
    assert res_home.stdout.strip() == "/home/user"

    # 3. Check ID
    res_id = await runtime.execute("id -u", "bash", mock_user_context, "sid")
    assert res_id.exit_code == 0
    # The uid for a created user is usually 1000, ensuring it's not 0 (root)
    assert res_id.stdout.strip() != "0"


@pytest.mark.live
@pytest.mark.asyncio
async def test_working_directory_default(
    filesystem_docker_runtime: DockerRuntime, mock_user_context: UserContext
) -> None:
    """Verify that execution starts in /home/user."""
    runtime = filesystem_docker_runtime

    # Check via PWD
    res_pwd = await runtime.execute("pwd", "bash", mock_user_context, "sid")
    assert res_pwd.exit_code == 0
    assert res_pwd.stdout.strip() == "/home/user"

    # Check via Python os.getcwd()
    res_py = await runtime.execute("import os; print(os.getcwd())", "python", mock_user_context, "sid")
    assert res_py.exit_code == 0
    assert res_py.stdout.strip() == "/home/user"


@pytest.mark.live
@pytest.mark.asyncio
async def test_permission_boundaries(filesystem_docker_runtime: DockerRuntime, mock_user_context: UserContext) -> None:
    """Verify that the user cannot write to root-owned paths."""
    runtime = filesystem_docker_runtime

    # Attempt to write to /root
    res_root = await runtime.execute("touch /root/hack.txt", "bash", mock_user_context, "sid")
    assert res_root.exit_code != 0
    # Different systems report perm denied differently in stderr/stdout/exit code
    assert "Permission denied" in res_root.stderr or "Permission denied" in res_root.stdout or res_root.exit_code == 1

    # Attempt to write to /usr
    res_usr = await runtime.execute("touch /usr/hack.txt", "bash", mock_user_context, "sid")
    assert res_usr.exit_code != 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_subdirectory_persistence_and_listing(
    filesystem_docker_runtime: DockerRuntime, mock_user_context: UserContext
) -> None:
    """Verify creating subdirectories and files works as expected in user home."""
    runtime = filesystem_docker_runtime

    # 1. Create Subdir
    await runtime.execute("mkdir -p subdir/nested", "bash", mock_user_context, "sid")

    # 2. Write file
    await runtime.execute("echo 'secret' > subdir/nested/file.txt", "bash", mock_user_context, "sid")

    # 3. List files via Runtime API (using relative path)
    files = await runtime.list_files("subdir/nested", mock_user_context, "sid")
    assert "file.txt" in files

    # 4. Verify Content
    res_cat = await runtime.execute("cat subdir/nested/file.txt", "bash", mock_user_context, "sid")
    assert res_cat.stdout.strip() == "secret"


@pytest.mark.live
@pytest.mark.asyncio
async def test_python_path_consistency(
    filesystem_docker_runtime: DockerRuntime, mock_user_context: UserContext
) -> None:
    """Verify that Python environment is healthy in the new user context."""
    runtime = filesystem_docker_runtime

    # Ensure pip is available and user can install (if simulated) or at least check version
    res_pip = await runtime.execute("pip --version", "bash", mock_user_context, "sid")
    assert res_pip.exit_code == 0

    # Ensure we are using the system/local python
    res_which = await runtime.execute("which python", "bash", mock_user_context, "sid")
    assert res_which.exit_code == 0

    # Verify we can write pyc files (implied by execution usually, but good to check write permissions in execution dir)
    res_py = await runtime.execute("import sys; print(sys.executable)", "python", mock_user_context, "sid")
    assert res_py.exit_code == 0
