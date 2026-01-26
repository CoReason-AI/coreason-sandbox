import asyncio
import io
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Literal

import docker
from docker.errors import DockerException
from docker.models.containers import Container
from loguru import logger
from packaging.requirements import Requirement

from coreason_sandbox.artifacts import ArtifactManager
from coreason_sandbox.models import ExecutionResult, FileReference
from coreason_sandbox.runtime import SandboxRuntime


class DockerRuntime(SandboxRuntime):
    """
    Docker-based implementation of the SandboxRuntime.
    """

    def __init__(
        self,
        image: str = "python:3.12-slim",
        cpu_limit: float = 1.0,
        mem_limit: str = "512m",
        allowed_packages: set[str] | None = None,
        timeout: float = 60.0,
        artifact_manager: ArtifactManager | None = None,
    ):
        self.client = docker.from_env()
        self.image = image
        self.cpu_limit = cpu_limit
        self.mem_limit = mem_limit
        self.allowed_packages = allowed_packages or set()
        self.timeout = timeout
        self.container: Container | None = None
        self.artifact_manager = artifact_manager or ArtifactManager()
        self.work_dir = "/home/user"

    async def start(self) -> None:
        """
        Boot the environment.
        """
        logger.info(f"Starting Docker sandbox with image {self.image}")
        try:
            self.container = self.client.containers.run(
                self.image,
                command="tail -f /dev/null",
                detach=True,
                network_mode="none",
                mem_limit=self.mem_limit,
                nano_cpus=int(self.cpu_limit * 1e9),
                remove=True,
                working_dir=self.work_dir,
            )
            # Ensure working directory exists
            self.container.exec_run(f"mkdir -p {self.work_dir}")

            logger.info(f"Docker sandbox started: {self.container.short_id}")
        except DockerException as e:
            logger.error(f"Failed to start Docker sandbox: {e}")
            raise

    async def _list_files_internal(self, path: str) -> set[str]:
        """Helper to list files for artifact detection."""
        try:
            files = await self.list_files(path)
            return set(files)
        except Exception:
            return set()

    async def list_files(self, path: str) -> list[str]:
        """
        List files in the directory.
        """
        if not self.container:
            raise RuntimeError("Sandbox not started")

        # Use ls -1
        # Check if path is absolute or relative
        if not path.startswith("/"):
            path = f"{self.work_dir}/{path}"

        exit_code, output = self.container.exec_run(f"ls -1 {path}")
        if exit_code != 0:
            # Could be not found or error
            stderr = output.decode("utf-8") if output else "Unknown error"
            logger.warning(f"Failed to list files at {path}: {stderr}")
            return []

        files = output.decode("utf-8").splitlines()
        return [f.strip() for f in files if f.strip()]

    def _download_and_package(self, package_name: str) -> bytes:
        """
        Download package wheels and package them into a tar stream.
        Runs synchronously (CPU/IO bound).
        """
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                package_name,
                "--dest",
                str(temp_dir),
                "--only-binary=:all:",
            ]

            # Handle cross-platform: if host is not Linux, force Linux wheels
            if platform.system().lower() != "linux":
                # Assuming container is standard linux (manylinux)
                # Detect arch
                machine = platform.machine().lower()
                if "arm" in machine or "aarch64" in machine:
                    plat = "manylinux2014_aarch64"
                else:
                    plat = "manylinux2014_x86_64"

                cmd.extend(
                    [
                        "--platform",
                        plat,
                        "--python-version",
                        "3.12",
                        "--implementation",
                        "cp",
                        "--abi",
                        "cp312",
                    ]
                )

            try:
                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to download package {package_name} on host: {e.stderr}")
                raise RuntimeError(f"Failed to download package {package_name}: {e.stderr}") from e

            # Tar the directory
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(temp_dir, arcname=".")
            tar_stream.seek(0)
            return tar_stream.getvalue()

    async def install_package(self, package_name: str) -> None:
        """
        Install a package dependency (pip only).
        """
        if not self.container:
            raise RuntimeError("Sandbox not started")

        try:
            req = Requirement(package_name)
            base_package_name = req.name.lower()
        except Exception as e:
            raise ValueError(f"Invalid package requirement: {package_name}") from e

        # Normalize allowlist to lowercase for check
        allowed_lower = {p.lower() for p in self.allowed_packages}

        if base_package_name not in allowed_lower:
            raise ValueError(f"Package {package_name} (base: {base_package_name}) is not in the allowed list.")

        logger.info(f"Installing package {package_name} via host proxy")

        # 1. Download & Package (Offload to thread)
        try:
            tar_bytes = await asyncio.to_thread(self._download_and_package, package_name)
        except RuntimeError as e:
            raise e

        # 2. Upload wheels to container
        remote_pkg_dir = f"/tmp/packages/{package_name}"
        self.container.exec_run(f"mkdir -p {remote_pkg_dir}")

        self.container.put_archive(path=remote_pkg_dir, data=tar_bytes)

        # 3. Install offline
        cmd = [
            "pip",
            "install",
            "--no-index",
            "--find-links",
            remote_pkg_dir,
            package_name,
        ]
        exit_code, output = self.container.exec_run(cmd)
        if exit_code != 0:
            msg = output.decode("utf-8")
            logger.error(f"Failed to install {package_name} in container: {msg}")
            raise RuntimeError(f"Failed to install package: {msg}")

    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:
        """
        Run script and capture output.
        """
        if not self.container:
            raise RuntimeError("Sandbox not started")

        logger.info(f"Executing {language} code in sandbox {self.container.short_id}")

        files_before = await self._list_files_internal(self.work_dir)

        # Prepare the command based on language
        cmd: list[str]
        if language == "python":
            cmd = ["python", "-c", code]
        elif language == "bash":
            cmd = ["bash", "-c", code]
        elif language == "r":
            cmd = ["Rscript", "-e", code]
        else:
            raise ValueError(f"Unsupported language: {language}")

        start_time = time.time()
        try:
            try:
                # Offload blocking Docker call to thread and enforce timeout
                exit_code, output = await asyncio.wait_for(
                    asyncio.to_thread(self.container.exec_run, cmd, demux=True),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError as e:
                logger.warning(
                    f"Execution timed out ({self.timeout}s). "
                    f"Restarting container {self.container.short_id} to cleanup process."
                )
                await asyncio.to_thread(self.container.restart)
                raise TimeoutError(f"Execution exceeded {self.timeout} seconds limit.") from e

            duration = time.time() - start_time

            stdout_bytes, stderr_bytes = output if output else (None, None)
            stdout_str = stdout_bytes.decode("utf-8") if stdout_bytes else ""
            stderr_str = stderr_bytes.decode("utf-8") if stderr_bytes else ""

            # Artifact detection
            files_after = await self._list_files_internal(self.work_dir)
            new_files = files_after - files_before

            artifacts: list[FileReference] = []

            with tempfile.TemporaryDirectory() as tmp_dir_str:
                tmp_dir = Path(tmp_dir_str)
                for filename in new_files:
                    remote_path = f"{self.work_dir}/{filename}"
                    local_path = tmp_dir / filename
                    try:
                        await self.download(remote_path, local_path)
                        ref = self.artifact_manager.process_file(local_path, filename)
                        artifacts.append(ref)
                    except Exception as e:
                        logger.warning(f"Failed to retrieve artifact {filename}: {e}")

            result = ExecutionResult(
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=exit_code,
                artifacts=artifacts,
                execution_duration=duration,
            )

            return result

        except DockerException as e:
            logger.error(f"Execution failed: {e}")
            raise

    async def upload(self, local_path: Path, remote_path: str) -> None:
        """
        Inject file into the sandbox.
        """
        if not self.container:
            raise RuntimeError("Sandbox not started")

        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        logger.info(f"Uploading {local_path} to {remote_path} in sandbox")

        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar.add(local_path, arcname=os.path.basename(remote_path))
        tar_stream.seek(0)

        parent_dir = os.path.dirname(remote_path) or "/"
        try:
            self.container.put_archive(path=parent_dir, data=tar_stream)
        except DockerException as e:
            logger.error(f"Upload failed: {e}")
            raise

    async def download(self, remote_path: str, local_path: Path) -> None:
        """
        Retrieve file from the sandbox.
        """
        if not self.container:
            raise RuntimeError("Sandbox not started")

        logger.info(f"Downloading {remote_path} to {local_path} from sandbox")

        try:
            bits, stat = self.container.get_archive(remote_path)

            tar_stream = io.BytesIO()
            for chunk in bits:
                tar_stream.write(chunk)
            tar_stream.seek(0)

            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                member = tar.next()
                if member is None:
                    raise FileNotFoundError(f"Remote file not found in archive: {remote_path}")

                f = tar.extractfile(member)
                if f is None:
                    raise RuntimeError("Failed to extract file from archive")

                with open(local_path, "wb") as local_f:
                    local_f.write(f.read())

        except DockerException as e:
            logger.error(f"Download failed: {e}")
            raise
        except FileNotFoundError:
            logger.error(f"Remote file not found: {remote_path}")
            raise

    async def terminate(self) -> None:
        """
        Kill and cleanup the sandbox environment.
        """
        if self.container:
            logger.info(f"Terminating Docker sandbox: {self.container.short_id}")
            try:
                self.container.kill()
            except DockerException as e:
                logger.warning(f"Error terminating Docker sandbox: {e}")
            finally:
                self.container = None
        else:
            logger.warning("Attempted to terminate non-existent Docker sandbox")
