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
async def test_upload_exception(docker_runtime: DockerRuntime, tmp_path: Any) -> None:
    local_file = tmp_path / "test.txt"
    local_file.write_text("content")

    # Cast to avoid mypy error if container could be None (it's set in fixture)
    assert docker_runtime.container is not None
    docker_runtime.container.put_archive.side_effect = DockerException("Upload failed")

    # Current implementation logs error and re-raises
    with pytest.raises(DockerException):
        await docker_runtime.upload(local_file, "remote.txt")


@pytest.mark.asyncio
async def test_download_docker_exception(docker_runtime: DockerRuntime, tmp_path: Any) -> None:
    assert docker_runtime.container is not None
    docker_runtime.container.get_archive.side_effect = DockerException("Download failed")

    dest = tmp_path / "dest.txt"
    with pytest.raises(DockerException):
        await docker_runtime.download("remote.txt", dest)


@pytest.mark.asyncio
async def test_download_file_not_found_exception(docker_runtime: DockerRuntime, tmp_path: Any) -> None:
    assert docker_runtime.container is not None
    # Simulate NotFound from Docker (subclass of DockerException)
    docker_runtime.container.get_archive.side_effect = NotFound("File not found")

    dest = tmp_path / "dest.txt"
    with pytest.raises(DockerException):
        await docker_runtime.download("remote.txt", dest)


@pytest.mark.asyncio
async def test_download_tar_extraction_exception(docker_runtime: DockerRuntime, tmp_path: Any) -> None:
    assert docker_runtime.container is not None
    # Mock success for get_archive but return empty/invalid tar?
    # get_archive returns (bits, stat)
    # We want to fail inside the `with tarfile.open` block or `tar.next()`

    # Mock a tar that is valid but empty (so next() raises StopIteration? No, returns None)
    import io
    import tarfile

    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w"):
        pass  # Empty tar
    tar_stream.seek(0)

    docker_runtime.container.get_archive.return_value = ([tar_stream.getvalue()], {})

    dest = tmp_path / "dest.txt"
    # Logic: member = tar.next(); if member is None: raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        await docker_runtime.download("remote.txt", dest)


@pytest.mark.asyncio
async def test_download_tar_extract_file_none(docker_runtime: DockerRuntime, tmp_path: Any) -> None:
    assert docker_runtime.container is not None

    # Mock a tar with a directory member (extractfile returns None)
    import io
    import tarfile

    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        info = tarfile.TarInfo("dir")
        info.type = tarfile.DIRTYPE
        tar.addfile(info)
    tar_stream.seek(0)

    docker_runtime.container.get_archive.return_value = ([tar_stream.getvalue()], {})

    dest = tmp_path / "dest.txt"
    with pytest.raises(RuntimeError, match="Failed to extract file"):
        await docker_runtime.download("remote", dest)
