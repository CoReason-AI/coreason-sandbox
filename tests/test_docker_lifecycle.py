from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from coreason_sandbox.runtimes.docker import DockerRuntime
from docker.errors import DockerException


@pytest.fixture
def mock_docker_client() -> Any:
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock:
        yield mock


@pytest.fixture
def docker_runtime(mock_docker_client: Any) -> DockerRuntime:
    return DockerRuntime()


@pytest.mark.asyncio
async def test_start_success(docker_runtime: DockerRuntime, mock_docker_client: Any) -> None:
    mock_container = MagicMock()
    mock_container.short_id = "test_id"
    mock_docker_client.return_value.containers.run.return_value = mock_container

    await docker_runtime.start()

    mock_docker_client.return_value.containers.run.assert_called_once()
    assert docker_runtime.container == mock_container

    # Check arguments
    call_args = mock_docker_client.return_value.containers.run.call_args
    assert call_args[0][0] == "python:3.12-slim"
    assert call_args[1]["network_mode"] == "none"
    assert call_args[1]["remove"] is True
    assert call_args[1]["working_dir"] == "/home/user"


@pytest.mark.asyncio
async def test_start_failure(docker_runtime: DockerRuntime, mock_docker_client: Any) -> None:
    mock_docker_client.return_value.containers.run.side_effect = DockerException("Start failed")

    with pytest.raises(DockerException):
        await docker_runtime.start()

    assert docker_runtime.container is None


@pytest.mark.asyncio
async def test_terminate_success(docker_runtime: DockerRuntime, mock_docker_client: Any) -> None:
    mock_container = MagicMock()
    mock_container.short_id = "test_id"
    docker_runtime.container = mock_container

    await docker_runtime.terminate()

    mock_container.kill.assert_called_once()
    assert docker_runtime.container is None


@pytest.mark.asyncio
async def test_terminate_no_container(docker_runtime: DockerRuntime) -> None:
    # Should not raise exception
    await docker_runtime.terminate()
    assert docker_runtime.container is None


@pytest.mark.asyncio
async def test_terminate_failure(docker_runtime: DockerRuntime) -> None:
    mock_container = MagicMock()
    mock_container.kill.side_effect = DockerException("Kill failed")
    docker_runtime.container = mock_container

    # Should log warning but not raise exception (fail open/safe)
    await docker_runtime.terminate()

    mock_container.kill.assert_called_once()
    assert docker_runtime.container is None


@pytest.mark.asyncio
async def test_list_files_success(docker_runtime: DockerRuntime, mock_user_context: Any) -> None:
    docker_runtime.container = MagicMock()
    docker_runtime.container.exec_run.return_value = (0, b"file1\nfile2\n")

    files = await docker_runtime.list_files(".", mock_user_context, "sid")

    assert files == ["file1", "file2"]


@pytest.mark.asyncio
async def test_list_files_failure(docker_runtime: DockerRuntime, mock_user_context: Any) -> None:
    docker_runtime.container = MagicMock()
    docker_runtime.container.exec_run.return_value = (1, b"Error")

    files = await docker_runtime.list_files(".", mock_user_context, "sid")
    assert files == []


@pytest.mark.asyncio
async def test_list_files_no_container(docker_runtime: DockerRuntime, mock_user_context: Any) -> None:
    with pytest.raises(RuntimeError, match="Sandbox not started"):
        await docker_runtime.list_files(".", mock_user_context, "sid")


@pytest.mark.asyncio
async def test_list_files_internal_exception(docker_runtime: DockerRuntime, mock_user_context: Any) -> None:
    # _list_files_internal suppresses exceptions
    with patch.object(docker_runtime, "list_files", side_effect=Exception("Fail")):
        files = await docker_runtime._list_files_internal(".", mock_user_context, "sid")
        assert files == set()
