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
    runtime.container = MagicMock()
    runtime.container.short_id = "test_id"
    return runtime


@pytest.mark.asyncio
async def test_execute_captures_artifacts(docker_runtime: DockerRuntime) -> None:
    # Mock exec_run for list_files (before)
    # Mock exec_run for execution
    # Mock exec_run for list_files (after)
    # Mock download logic (self.container.get_archive)

    # We need to control the sequence of calls to exec_run
    # 1. list_files (mkdir -p is called in start(), but we are mocking runtime without start calling)
    # Actually wait, `start` calls `mkdir`, but here we inject container mock.

    # Sequence of exec_run calls in execute():
    # 1. ls -1 /home/sandbox (before)
    # 2. cmd execution
    # 3. ls -1 /home/sandbox (after)

    # We must cast container to MagicMock to satisfy mypy
    container_mock = docker_runtime.container
    assert container_mock is not None

    container_mock.exec_run.side_effect = [
        (0, b""),  # Before: empty
        (0, (b"output", b"")),  # Execution
        (0, b"plot.png\n"),  # After: plot.png
    ]

    # Mock download of plot.png
    # get_archive returns (bits, stat)
    import io
    import tarfile

    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tar_info = tarfile.TarInfo(name="plot.png")
        tar_info.size = 4
        tar.addfile(tar_info, io.BytesIO(b"data"))
    tar_stream.seek(0)

    container_mock.get_archive.return_value = ([tar_stream.getvalue()], {})

    result = await docker_runtime.execute("create_plot()", "python")

    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.filename == "plot.png"
    assert artifact.content_type == "image/png"
    # Base64 of 'data' is 'ZGF0YQ=='
    assert artifact.url is not None and "data:image/png;base64,ZGF0YQ==" in artifact.url


@pytest.mark.asyncio
async def test_artifact_manager_processing(tmp_path: Any) -> None:
    from coreason_sandbox.artifacts import ArtifactManager

    manager = ArtifactManager()

    # Test Image
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"image_data")

    ref = manager.process_file(img_path, "test.png")
    assert ref.content_type == "image/png"
    assert ref.url is not None and "base64" in ref.url

    # Test Text/Other
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("hello")

    ref = manager.process_file(txt_path, "test.txt")
    assert ref.content_type == "text/plain"
    assert ref.url is None  # No storage configured


@pytest.mark.asyncio
async def test_artifact_manager_storage(tmp_path: Any) -> None:
    from coreason_sandbox.artifacts import ArtifactManager

    mock_storage = MagicMock()
    mock_storage.upload_file.return_value = "http://s3/test.pdf"

    manager = ArtifactManager(storage=mock_storage)

    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"pdf_data")

    ref = manager.process_file(pdf_path, "test.pdf")
    assert ref.content_type == "application/pdf"
    assert ref.url == "http://s3/test.pdf"
