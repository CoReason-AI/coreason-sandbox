import io
import tarfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import DockerException, NotFound

from coreason_sandbox.runtimes.docker import DockerRuntime


@pytest.fixture
def mock_docker_client() -> Any:
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock:
        yield mock


@pytest.fixture
def docker_runtime(mock_docker_client: Any) -> DockerRuntime:
    runtime = DockerRuntime()
    runtime.container = MagicMock()
    runtime.container.short_id = "test_id"
    return runtime


@pytest.mark.asyncio
async def test_upload_success(docker_runtime: DockerRuntime, tmp_path: Any, mock_user_context: Any) -> None:
    # Create a dummy local file
    local_file = tmp_path / "test.txt"
    local_file.write_text("content")

    await docker_runtime.upload(local_file, "/remote/path/test.txt", mock_user_context, "sid")

    # We mock container, so we access it via the property but need to assert it's not None
    assert docker_runtime.container is not None
    docker_runtime.container.put_archive.assert_called_once()
    args, kwargs = docker_runtime.container.put_archive.call_args

    # Check if positional args are used or kwargs
    path_arg = kwargs.get("path") or args[0]
    assert path_arg == "/remote/path"

    # Verify the tar stream contains the file
    tar_bytes = kwargs["data"]
    tar_bytes.seek(0)
    with tarfile.open(fileobj=tar_bytes, mode="r") as tar:
        names = tar.getnames()
        assert "test.txt" in names


@pytest.mark.asyncio
async def test_upload_no_file(docker_runtime: DockerRuntime, tmp_path: Any, mock_user_context: Any) -> None:
    local_file = tmp_path / "non_existent.txt"
    with pytest.raises(FileNotFoundError):
        await docker_runtime.upload(local_file, "/remote/path", mock_user_context, "sid")


@pytest.mark.asyncio
async def test_upload_no_container(mock_docker_client: Any, tmp_path: Any, mock_user_context: Any) -> None:
    runtime = DockerRuntime()
    local_file = tmp_path / "test.txt"
    local_file.write_text("content")

    with pytest.raises(RuntimeError, match="Sandbox not started"):
        await runtime.upload(local_file, "/remote", mock_user_context, "sid")


@pytest.mark.asyncio
async def test_download_success(docker_runtime: DockerRuntime, tmp_path: Any, mock_user_context: Any) -> None:
    # Mock get_archive return value
    # Generator of bytes representing a tar file
    file_content = b"remote content"
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tar_info = tarfile.TarInfo(name="remote.txt")
        tar_info.size = len(file_content)
        tar.addfile(tar_info, io.BytesIO(file_content))
    tar_stream.seek(0)

    # get_archive returns (iterable, stat)
    assert docker_runtime.container is not None
    docker_runtime.container.get_archive.return_value = ([tar_stream.getvalue()], {})

    dest_path = tmp_path / "downloaded.txt"
    await docker_runtime.download("/remote/remote.txt", dest_path, mock_user_context, "sid")

    assert dest_path.exists()
    assert dest_path.read_bytes() == file_content


@pytest.mark.asyncio
async def test_download_not_found(docker_runtime: DockerRuntime, tmp_path: Any, mock_user_context: Any) -> None:
    # Simulate Docker NotFound exception
    assert docker_runtime.container is not None
    docker_runtime.container.get_archive.side_effect = NotFound("File not found")

    dest_path = tmp_path / "downloaded.txt"
    # Our code catches DockerException (parent of NotFound) and logs error but re-raises

    with pytest.raises((DockerException, FileNotFoundError, Exception)):
        await docker_runtime.download("/remote/missing.txt", dest_path, mock_user_context, "sid")


@pytest.mark.asyncio
async def test_download_no_container(mock_docker_client: Any, tmp_path: Any, mock_user_context: Any) -> None:
    runtime = DockerRuntime()
    dest_path = tmp_path / "dest.txt"
    with pytest.raises(RuntimeError, match="Sandbox not started"):
        await runtime.download("/remote", dest_path, mock_user_context, "sid")
