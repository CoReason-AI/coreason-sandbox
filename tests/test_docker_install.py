import subprocess
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from coreason_sandbox.runtimes.docker import DockerRuntime


@pytest.fixture
def mock_docker_client() -> Any:
    with patch("coreason_sandbox.runtimes.docker.docker.from_env") as mock:
        yield mock


@pytest.fixture
def docker_runtime(mock_docker_client: Any) -> Any:
    # Explicitly allow pandas for testing
    runtime = DockerRuntime(allowed_packages={"pandas"})
    runtime.container = MagicMock()
    runtime.container.short_id = "test_id"
    return runtime


@pytest.mark.asyncio
async def test_install_package_success(docker_runtime: Any) -> None:
    # 1. Download/tar (mocked)
    with patch("coreason_sandbox.runtimes.docker.DockerRuntime._download_and_package", return_value=b"tar_data"):
        # 2. Upload/install (mocked container)
        docker_runtime.container.exec_run.return_value = (0, b"Success")

        await docker_runtime.install_package("pandas")

        # Verify upload
        docker_runtime.container.put_archive.assert_called_once()
        args, kwargs = docker_runtime.container.put_archive.call_args

        path_arg = kwargs.get("path")
        if not path_arg and args:
            path_arg = args[0]

        assert path_arg == "/tmp/packages/pandas"
        assert kwargs["data"] == b"tar_data"

        # Verify install cmd
        docker_runtime.container.exec_run.assert_called()
        cmd = docker_runtime.container.exec_run.call_args[0][0]
        assert "pip install" in " ".join(cmd)
        assert "pandas" in cmd


@pytest.mark.asyncio
async def test_install_package_not_allowed(docker_runtime: Any) -> None:
    # requests is not in allowed_packages={"pandas"}
    with pytest.raises(ValueError, match="is not in the allowed list"):
        await docker_runtime.install_package("requests")


@pytest.mark.asyncio
async def test_install_package_invalid_name(docker_runtime: Any) -> None:
    """Test that invalid package names raise ValueError."""
    with pytest.raises(ValueError, match="Invalid package requirement"):
        await docker_runtime.install_package("!invalid-package-name")


@pytest.mark.asyncio
async def test_install_package_install_failed(docker_runtime: Any) -> None:
    with patch("coreason_sandbox.runtimes.docker.DockerRuntime._download_and_package", return_value=b"tar_data"):
        docker_runtime.container.exec_run.return_value = (1, b"Install error")

        with pytest.raises(RuntimeError, match="Failed to install package"):
            await docker_runtime.install_package("pandas")


@pytest.mark.asyncio
async def test_install_package_download_failed(docker_runtime: Any) -> None:
    """Test re-raising RuntimeError from _download_and_package."""
    with patch(
        "coreason_sandbox.runtimes.docker.DockerRuntime._download_and_package",
        side_effect=RuntimeError("Download fail")
    ):
        with pytest.raises(RuntimeError, match="Download fail"):
            await docker_runtime.install_package("pandas")


@pytest.mark.asyncio
async def test_install_package_no_container(mock_docker_client: Any) -> None:
    """Test installing package without a started container."""
    # Ensure mock_docker_client is used to avoid real docker connection
    runtime = DockerRuntime()  # Not started
    with pytest.raises(RuntimeError, match="Sandbox not started"):
        await runtime.install_package("pandas")


def test_download_and_package_logic(docker_runtime: Any) -> None:
    """
    Test _download_and_package logic by mocking subprocess and tarfile.
    """
    package_name = "pandas"

    with (
        patch("subprocess.run") as mock_run,
        patch("tarfile.open"),
        patch("io.BytesIO") as mock_io,
        patch("tempfile.TemporaryDirectory") as mock_temp,
    ):
        mock_temp.return_value.__enter__.return_value = "/tmp/fake_dir"
        mock_io.return_value.getvalue.return_value = b"fake_tar_bytes"

        # Test 1: Linux host (simple path)
        with patch("platform.system", return_value="Linux"):
            data = docker_runtime._download_and_package(package_name)
            assert data == b"fake_tar_bytes"

            mock_run.assert_called()
            args = mock_run.call_args[0][0]
            assert "pip" in args
            assert "download" in args
            assert package_name in args
            # Ensure no platform args for linux
            assert "--platform" not in args

        # Test 2: Non-Linux host (x86_64)
        with patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="x86_64"):
            docker_runtime._download_and_package(package_name)

            args = mock_run.call_args[0][0]
            assert "--platform" in args
            assert "manylinux2014_x86_64" in args

        # Test 3: Non-Linux host (ARM/aarch64)
        with patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="arm64"):
            docker_runtime._download_and_package(package_name)

            args = mock_run.call_args[0][0]
            assert "--platform" in args
            assert "manylinux2014_aarch64" in args

        # Test 4: Subprocess failure
        mock_run.side_effect = subprocess.CalledProcessError(1, cmd="pip", stderr="Fail")
        with pytest.raises(RuntimeError, match="Failed to download package"):
            docker_runtime._download_and_package(package_name)
