import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar

from e2b_code_interpreter import Sandbox as E2BSandbox
from loguru import logger

from coreason_sandbox.artifacts import ArtifactManager
from coreason_sandbox.models import ExecutionResult, FileReference
from coreason_sandbox.runtime import SandboxRuntime

T = TypeVar("T")


class E2BRuntime(SandboxRuntime):
    """E2B Cloud implementation of the SandboxRuntime.

    Uses E2B cloud-based microVMs for secure and scalable code execution.
    """

    def __init__(
        self,
        api_key: str | None = None,
        template: str = "base",
        timeout: float = 60.0,
        artifact_manager: ArtifactManager | None = None,
    ):
        """Initializes the E2BRuntime.

        Args:
            api_key: E2B API Key. Defaults to E2B_API_KEY env var.
            template: E2B template ID to use (default: 'base').
            timeout: Execution timeout in seconds.
            artifact_manager: Manager for processing artifacts.
        """
        self.api_key = api_key or os.getenv("E2B_API_KEY")
        self.template = template
        self.timeout = timeout
        self.sandbox: E2BSandbox | None = None
        self.artifact_manager = artifact_manager or ArtifactManager()

    async def start(self) -> None:
        """Boot the environment.

        Initializes and starts the E2B sandbox session.
        If a session is already active, it is terminated first.

        Raises:
            Exception: If the sandbox fails to start.
        """
        if self.sandbox:
            logger.warning("E2B sandbox already running. Terminating old session before restart.")
            await self.terminate()

        logger.info(f"Starting E2B sandbox (template: {self.template})")
        try:
            self.sandbox = await asyncio.to_thread(
                E2BSandbox,
                api_key=self.api_key,
            )
            # Use local variable to satisfy mypy or assert
            sandbox = self.sandbox
            assert sandbox is not None
            logger.info(f"E2B sandbox started: {sandbox.sandbox_id}")
        except Exception as e:
            logger.error(f"Failed to start E2B sandbox: {e}")
            raise

    async def install_package(self, package_name: str) -> None:
        """Install a package dependency.

        Uses pip to install the package inside the E2B sandbox.

        Args:
            package_name: The name of the package to install.

        Raises:
            RuntimeError: If the sandbox is not started.
            Exception: If installation fails.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not started")

        logger.info(f"Installing {package_name} in E2B sandbox")
        try:
            # E2B SDK doesn't have explicit install_package method?
            # e2b_code_interpreter.Sandbox has commands.run
            # But check if there is a specialized method.
            # According to docs, `sandbox.commands.run("pip install ...")` is standard.
            await asyncio.to_thread(self.sandbox.commands.run, f"pip install {package_name}")
        except Exception as e:
            logger.error(f"Failed to install package: {e}")
            raise

    async def list_files(self, path: str) -> list[str]:
        """List files in the directory.

        Args:
            path: The directory path to list.

        Returns:
            list[str]: A list of filenames.

        Raises:
            RuntimeError: If the sandbox is not started.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not started")

        try:
            # E2B SDK has `files.list(path)`
            entries = await asyncio.to_thread(self.sandbox.files.list, path)
            # entries is List[EntryInfo]
            return [entry.name for entry in entries]
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    async def _list_files_internal(self, path: str) -> set[str]:
        """Helper to list files for artifact detection.

        Args:
            path: The directory path to list.

        Returns:
            set[str]: A set of filenames.
        """
        try:
            files = await self.list_files(path)
            return set(files)
        except Exception:
            return set()

    async def _run_sdk_command(self, func: Callable[..., T], *args: Any) -> T:
        """Helper to run an SDK command in a thread with timeout enforcement.

        Restarts sandbox on timeout to ensure cleanup.

        Args:
            func: The SDK function to call.
            *args: Arguments for the function.

        Returns:
            T: The result of the function call.

        Raises:
            TimeoutError: If execution exceeds the timeout.
            Exception: If the SDK command fails.
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(func, *args),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError as e:
            logger.warning(f"Execution timed out ({self.timeout}s). Restarting sandbox to cleanup process.")
            await self.terminate()
            await self.start()
            raise TimeoutError(f"Execution exceeded {self.timeout} seconds limit.") from e

    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:
        """Run script and capture output.

        Executes the code in the E2B sandbox and captures native artifacts (PNGs)
        as well as filesystem artifacts.

        Args:
            code: The source code to execute.
            language: The programming language.

        Returns:
            ExecutionResult: The execution result including output and artifacts.

        Raises:
            RuntimeError: If the sandbox is not started.
            ValueError: If the language is not supported.
            TimeoutError: If execution exceeds the timeout.
            Exception: If execution fails.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not started")

        logger.info(f"Executing {language} code in E2B sandbox")

        # Filesystem artifact detection: Snapshot before
        files_before = await self._list_files_internal(".")

        start_time = time.time()
        stdout = ""
        stderr = ""
        exit_code = 0
        artifacts = []

        try:
            if language == "python":
                execution = await self._run_sdk_command(self.sandbox.run_code, code)
                # execution is E2BExecution (though _run_sdk_command type hint is generic T)
                # We know specific type based on call

                stdout = "\n".join(log.content for log in execution.logs.stdout)
                stderr = "\n".join(log.content for log in execution.logs.stderr)

                if execution.error:
                    stderr += f"\n{execution.error.name}: {execution.error.value}\n{execution.error.traceback}"
                    exit_code = 1
                else:
                    exit_code = 0

                # 1. Native E2B artifacts (PNGs)
                for result in execution.results:
                    if hasattr(result, "png") and result.png:
                        artifacts.append(
                            FileReference(
                                filename=f"chart_{time.time()}.png",
                                path="memory",
                                content_type="image/png",
                                url=f"data:image/png;base64,{result.png}",
                            )
                        )
                    elif hasattr(result, "text") and result.text:
                        stdout += f"\n[Result]: {result.text}"

            elif language == "bash":
                cmd_result = await self._run_sdk_command(self.sandbox.commands.run, code)
                stdout = cmd_result.stdout
                stderr = cmd_result.stderr
                exit_code = cmd_result.exit_code

            elif language == "r":
                cmd_result = await self._run_sdk_command(self.sandbox.commands.run, f"Rscript -e '{code}'")
                stdout = cmd_result.stdout
                stderr = cmd_result.stderr
                exit_code = cmd_result.exit_code

            else:
                raise ValueError(f"Unsupported language: {language}")

            duration = time.time() - start_time

            # Filesystem artifact detection: Snapshot after
            files_after = await self._list_files_internal(".")
            new_files = files_after - files_before

            if new_files:
                with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir_str:
                    tmp_dir = Path(tmp_dir_str)
                    for filename in new_files:
                        remote_path = filename
                        local_path = tmp_dir / filename
                        try:
                            await self.download(remote_path, local_path)
                            ref = self.artifact_manager.process_file(local_path, filename)
                            artifacts.append(ref)
                        except Exception as e:
                            logger.warning(f"Failed to retrieve artifact {filename}: {e}")

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                artifacts=artifacts,
                execution_duration=duration,
            )

        except Exception as e:
            logger.error(f"E2B Execution failed: {e}")
            raise

    async def upload(self, local_path: Path, remote_path: str) -> None:
        """Inject file into the sandbox.

        Args:
            local_path: Path to the local file.
            remote_path: Destination path in the sandbox.

        Raises:
            RuntimeError: If the sandbox is not started.
            FileNotFoundError: If the local file does not exist.
            Exception: If upload fails.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not started")

        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        try:
            with open(local_path, "rb") as f:
                await asyncio.to_thread(self.sandbox.files.write, remote_path, f)
        except Exception as e:
            logger.error(f"E2B upload failed: {e}")
            raise

    async def download(self, remote_path: str, local_path: Path) -> None:
        """Retrieve file from the sandbox.

        Args:
            remote_path: Path to the file in the sandbox.
            local_path: Destination path on the host.

        Raises:
            RuntimeError: If the sandbox is not started.
            FileNotFoundError: If the remote file does not exist.
            Exception: If download fails.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not started")

        try:
            content_bytes = await asyncio.to_thread(self.sandbox.files.read, remote_path)

            if content_bytes is None:
                raise FileNotFoundError(f"Remote file not found: {remote_path}")

            with open(local_path, "wb") as f:
                f.write(content_bytes)
        except Exception as e:
            logger.error(f"E2B download failed: {e}")
            raise

    async def terminate(self) -> None:
        """Kill and cleanup the sandbox environment.

        Closes the E2B sandbox session.
        """
        if self.sandbox:
            logger.info(f"Terminating E2B sandbox: {self.sandbox.sandbox_id}")
            try:
                await asyncio.to_thread(self.sandbox.close)
            except Exception as e:
                logger.warning(f"Error terminating E2B sandbox: {e}")
            finally:
                self.sandbox = None
        else:
            logger.warning("Attempted to terminate non-existent E2B sandbox")
