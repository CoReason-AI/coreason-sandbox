import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Literal

from e2b_code_interpreter import Sandbox as E2BSandbox
from e2b_code_interpreter.models import Execution as E2BExecution
from loguru import logger

from coreason_sandbox.models import ExecutionResult, FileReference
from coreason_sandbox.runtime import SandboxRuntime
from coreason_sandbox.utils.artifacts import ArtifactManager


class E2BRuntime(SandboxRuntime):
    """
    E2B Cloud implementation of the SandboxRuntime.
    """

    def __init__(
        self,
        api_key: str | None = None,
        template: str = "base",
        timeout: float = 60.0,
        artifact_manager: ArtifactManager | None = None,
    ):
        self.api_key = api_key or os.getenv("E2B_API_KEY")
        self.template = template
        self.timeout = timeout
        self.sandbox: E2BSandbox | None = None
        self.artifact_manager = artifact_manager or ArtifactManager()

    async def start(self) -> None:
        """
        Boot the environment.
        """
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
        """
        Install a package dependency.
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
        """
        List files in the directory.
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
        """Helper to list files for artifact detection."""
        try:
            files = await self.list_files(path)
            return set(files)
        except Exception:
            return set()

    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:
        """
        Run script and capture output.
        """
        if not self.sandbox:
            raise RuntimeError("Sandbox not started")

        logger.info(f"Executing {language} code in E2B sandbox")

        # Filesystem artifact detection: Snapshot before
        files_before = await self._list_files_internal(".")

        start_time = time.time()
        try:
            if language == "python":
                try:
                    execution: E2BExecution = await asyncio.wait_for(
                        asyncio.to_thread(self.sandbox.run_code, code),
                        timeout=self.timeout,
                    )
                except asyncio.TimeoutError as e:
                    logger.warning(f"Execution timed out ({self.timeout}s). " f"Restarting sandbox to cleanup process.")
                    await self.terminate()
                    await self.start()
                    raise TimeoutError(f"Execution exceeded {self.timeout} seconds limit.") from e

                stdout = "\n".join(log.content for log in execution.logs.stdout)
                stderr = "\n".join(log.content for log in execution.logs.stderr)

                if execution.error:
                    stderr += f"\n{execution.error.name}: {execution.error.value}\n{execution.error.traceback}"
                    exit_code = 1
                else:
                    exit_code = 0

                artifacts = []
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
                try:
                    cmd_result = await asyncio.wait_for(
                        asyncio.to_thread(self.sandbox.commands.run, code),
                        timeout=self.timeout,
                    )
                except asyncio.TimeoutError as e:
                    logger.warning(f"Execution timed out ({self.timeout}s). " f"Restarting sandbox to cleanup process.")
                    await self.terminate()
                    await self.start()
                    raise TimeoutError(f"Execution exceeded {self.timeout} seconds limit.") from e

                stdout = cmd_result.stdout
                stderr = cmd_result.stderr
                exit_code = cmd_result.exit_code
                artifacts = []

            elif language == "r":
                try:
                    cmd_result = await asyncio.wait_for(
                        asyncio.to_thread(self.sandbox.commands.run, f"Rscript -e '{code}'"),
                        timeout=self.timeout,
                    )
                except asyncio.TimeoutError as e:
                    logger.warning(f"Execution timed out ({self.timeout}s). " f"Restarting sandbox to cleanup process.")
                    await self.terminate()
                    await self.start()
                    raise TimeoutError(f"Execution exceeded {self.timeout} seconds limit.") from e

                stdout = cmd_result.stdout
                stderr = cmd_result.stderr
                exit_code = cmd_result.exit_code
                artifacts = []

            else:
                raise ValueError(f"Unsupported language: {language}")

            duration = time.time() - start_time

            # Filesystem artifact detection: Snapshot after
            files_after = await self._list_files_internal(".")
            new_files = files_after - files_before

            if new_files:
                with tempfile.TemporaryDirectory() as tmp_dir_str:
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
        """
        Inject file into the sandbox.
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
        """
        Retrieve file from the sandbox.
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
        """
        Kill and cleanup the sandbox environment.
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
