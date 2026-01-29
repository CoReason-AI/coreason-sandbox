from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from coreason_sandbox.runtimes.docker import DockerRuntime


@pytest.fixture
def mock_docker_client() -> Any:
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock:
        yield mock


@pytest.fixture
def docker_runtime(mock_docker_client: Any) -> DockerRuntime:
    runtime = DockerRuntime()
    # Mock container
    runtime.container = MagicMock()
    runtime.container.short_id = "test_id"
    return runtime


@pytest.mark.asyncio
async def test_path_resolution_relative_subdir(docker_runtime: DockerRuntime, mock_user_context: Any) -> None:
    """Verify that a relative path 'subdir' resolves to '/home/user/subdir'."""
    assert docker_runtime.container is not None
    # Mock successful ls
    docker_runtime.container.exec_run.return_value = (0, b"file.txt\n")

    await docker_runtime.list_files("subdir", mock_user_context, "sid")

    # Verify the command sent to docker
    docker_runtime.container.exec_run.assert_called_with("ls -1 /home/user/subdir")


@pytest.mark.asyncio
async def test_path_resolution_absolute(docker_runtime: DockerRuntime, mock_user_context: Any) -> None:
    """Verify that an absolute path is used as-is."""
    assert docker_runtime.container is not None
    docker_runtime.container.exec_run.return_value = (0, b"file.txt\n")

    await docker_runtime.list_files("/tmp/custom", mock_user_context, "sid")

    # Verify the command sent to docker
    docker_runtime.container.exec_run.assert_called_with("ls -1 /tmp/custom")


@pytest.mark.asyncio
async def test_path_resolution_dot(docker_runtime: DockerRuntime, mock_user_context: Any) -> None:
    """Verify that '.' resolves to '/home/user/.'."""
    assert docker_runtime.container is not None
    docker_runtime.container.exec_run.return_value = (0, b"file.txt\n")

    await docker_runtime.list_files(".", mock_user_context, "sid")

    docker_runtime.container.exec_run.assert_called_with("ls -1 /home/user/.")


@pytest.mark.asyncio
async def test_start_creates_home_directory(mock_docker_client: Any) -> None:
    """Verify that start() explicitly ensures /home/user exists."""
    runtime = DockerRuntime()
    mock_container = MagicMock()
    mock_container.short_id = "test_id"
    mock_docker_client.return_value.containers.run.return_value = mock_container

    await runtime.start()

    # Verify mkdir call
    # It might be called with other args, so we check specifically
    mock_container.exec_run.assert_called_with("mkdir -p /home/user")


@pytest.mark.asyncio
async def test_upload_tar_structure(docker_runtime: DockerRuntime, tmp_path: Any, mock_user_context: Any) -> None:
    """Verify that upload packs the file correctly relative to /home/user if needed."""
    # Note: upload uses os.path.dirname(remote_path) or "/" for put_archive path
    # and includes the basename in the tar.

    local_file = tmp_path / "data.txt"
    local_file.write_text("data")

    # Case 1: Upload to root of home
    await docker_runtime.upload(local_file, "/home/user/data.txt", mock_user_context, "sid")

    assert docker_runtime.container is not None
    args, kwargs = docker_runtime.container.put_archive.call_args
    dest_path = kwargs.get("path") or args[0]

    assert dest_path == "/home/user"

    # Case 2: Upload to subdir
    await docker_runtime.upload(local_file, "/home/user/subdir/data.txt", mock_user_context, "sid")

    args, kwargs = docker_runtime.container.put_archive.call_args
    dest_path = kwargs.get("path") or args[0]

    assert dest_path == "/home/user/subdir"
