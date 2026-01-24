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
    runtime = DockerRuntime(allowed_packages={"requests", "pandas"})
    # Mock a started container
    runtime.container = MagicMock()
    runtime.container.short_id = "test_id"
    return runtime


@pytest.mark.asyncio
async def test_install_package_success(docker_runtime: Any) -> None:
    # Mock _download_and_package to avoid threading complexity and focus on flow
    with patch.object(docker_runtime, "_download_and_package", return_value=b"tarbytes") as mock_download:
        # Setup exec_run side effects:
        # 1. mkdir (success)
        # 2. pip install (success)
        docker_runtime.container.exec_run.side_effect = [(0, b""), (0, b"Successfully installed requests")]

        await docker_runtime.install_package("requests")

        mock_download.assert_called_once_with("requests")

        # Verify upload
        docker_runtime.container.put_archive.assert_called_once_with(path="/tmp/packages/requests", data=b"tarbytes")

        # Verify install command
        install_call = docker_runtime.container.exec_run.call_args_list[1]
        cmd = install_call[0][0]
        assert "pip" in cmd
        assert "install" in cmd
        assert "--no-index" in cmd
        assert "requests" in cmd


def test_download_and_package_linux(docker_runtime: Any) -> None:
    """Test the synchronous helper method logic on Linux."""
    with (
        patch("coreason_sandbox.runtimes.docker.subprocess.run") as mock_subprocess,
        patch("coreason_sandbox.runtimes.docker.tarfile.open"),
        patch("platform.system", return_value="Linux"),
    ):
        docker_runtime._download_and_package("requests")

        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert "pip" in args
        assert "download" in args
        assert "--platform" not in args  # Should not add platform flags on Linux


def test_download_and_package_mac_x86(docker_runtime: Any) -> None:
    """Test the synchronous helper method logic on Mac (non-Linux) x86_64."""
    with (
        patch("coreason_sandbox.runtimes.docker.subprocess.run") as mock_subprocess,
        patch("coreason_sandbox.runtimes.docker.tarfile.open"),
        patch("platform.system", return_value="Darwin"),
        patch("platform.machine", return_value="x86_64"),
    ):
        docker_runtime._download_and_package("requests")

        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert "--platform" in args
        assert "manylinux2014_x86_64" in args
        assert "--python-version" in args


def test_download_and_package_mac_arm(docker_runtime: Any) -> None:
    """Test the synchronous helper method logic on Mac (non-Linux) ARM."""
    with (
        patch("coreason_sandbox.runtimes.docker.subprocess.run") as mock_subprocess,
        patch("coreason_sandbox.runtimes.docker.tarfile.open"),
        patch("platform.system", return_value="Darwin"),
        patch("platform.machine", return_value="arm64"),
    ):
        docker_runtime._download_and_package("requests")

        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert "--platform" in args
        assert "manylinux2014_aarch64" in args
        assert "--python-version" in args


def test_download_and_package_fail(docker_runtime: Any) -> None:
    with (
        patch(
            "coreason_sandbox.runtimes.docker.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "cmd", stderr="error"),
        ),
        patch("platform.system", return_value="Linux"),
    ):
        with pytest.raises(RuntimeError, match="Failed to download package requests: error"):
            docker_runtime._download_and_package("requests")


@pytest.mark.asyncio
async def test_install_package_not_allowed(docker_runtime: Any) -> None:
    with pytest.raises(ValueError, match="not in the allowed list"):
        await docker_runtime.install_package("malicious-package")


@pytest.mark.asyncio
async def test_install_package_not_started(mock_docker_client: Any) -> None:
    runtime = DockerRuntime()
    with pytest.raises(RuntimeError, match="Sandbox not started"):
        await runtime.install_package("requests")


@pytest.mark.asyncio
async def test_install_package_download_exception(docker_runtime: Any) -> None:
    """Test that runtime errors during download are propagated correctly."""
    # Simulate an error in the threaded function
    with patch.object(docker_runtime, "_download_and_package", side_effect=RuntimeError("Download failed")):
        with pytest.raises(RuntimeError, match="Download failed"):
            await docker_runtime.install_package("requests")


@pytest.mark.asyncio
async def test_install_package_install_fail(docker_runtime: Any) -> None:
    with patch.object(docker_runtime, "_download_and_package", return_value=b"tarbytes"):
        # exec_run side effects:
        # 1. mkdir (success)
        # 2. pip install (fail)
        docker_runtime.container.exec_run.side_effect = [(0, b""), (1, b"Could not find package")]

        with pytest.raises(RuntimeError, match="Failed to install package"):
            await docker_runtime.install_package("requests")


@pytest.mark.asyncio
async def test_install_package_with_version(docker_runtime: Any) -> None:
    """Test that installing a package with version specifier works if base name is allowed."""
    with patch.object(docker_runtime, "_download_and_package", return_value=b"tarbytes") as mock_download:
        docker_runtime.container.exec_run.side_effect = [(0, b""), (0, b"Success")]

        # "requests" is in allowlist
        await docker_runtime.install_package("requests==2.31.0")

        # Verify download called with full string
        mock_download.assert_called_once_with("requests==2.31.0")


@pytest.mark.asyncio
async def test_install_package_case_insensitive(docker_runtime: Any) -> None:
    """Test that package name checking is case insensitive."""
    with patch.object(docker_runtime, "_download_and_package", return_value=b"tarbytes") as mock_download:
        docker_runtime.container.exec_run.side_effect = [(0, b""), (0, b"Success")]

        # "Requests" should match "requests" in allowlist
        await docker_runtime.install_package("Requests")

        mock_download.assert_called_once_with("Requests")


@pytest.mark.asyncio
async def test_install_package_complex_specifiers(docker_runtime: Any) -> None:
    """Test parsing of complex version specifiers."""
    with patch.object(docker_runtime, "_download_and_package", return_value=b"tarbytes") as mock_download:
        docker_runtime.container.exec_run.side_effect = [(0, b""), (0, b"Success")]

        # "pandas" is in allowlist
        await docker_runtime.install_package("pandas>=1.0,<2.0")

        mock_download.assert_called_once_with("pandas>=1.0,<2.0")
