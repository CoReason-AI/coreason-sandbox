from typing import Any, Literal

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.factory import SandboxFactory
from coreason_sandbox.utils.veritas import VeritasIntegrator


class SandboxMCP:
    """
    MCP-compliant server logic wrapper for Coreason Sandbox.
    Exposes tools for the Agent.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.runtime = SandboxFactory.get_runtime(self.config)
        self.veritas = VeritasIntegrator()
        self.started = False

    async def ensure_started(self) -> None:
        if not self.started:
            await self.runtime.start()
            self.started = True

    async def execute_code(
        self, language: Literal["python", "bash", "r"], code: str
    ) -> dict[str, str | int | float | list[dict[str, Any]]]:
        """
        Execute code in the sandbox.
        """
        await self.ensure_started()

        # Veritas Audit Log
        await self.veritas.log_pre_execution(code, language)

        result = await self.runtime.execute(code, language)

        # Convert artifacts to simpler dicts for MCP response if needed
        artifacts_data = [
            {
                "filename": a.filename,
                "url": a.url,
                "content_type": a.content_type,
            }
            for a in result.artifacts
        ]

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "execution_duration": result.execution_duration,
            "artifacts": artifacts_data,
        }

    async def install_package(self, package_name: str) -> str:
        """
        Install a package in the sandbox.
        """
        await self.ensure_started()
        await self.runtime.install_package(package_name)
        return f"Package {package_name} installed successfully."

    async def list_files(self, path: str = ".") -> list[str]:
        """
        List files in the sandbox directory.
        """
        await self.ensure_started()
        return await self.runtime.list_files(path)

    async def shutdown(self) -> None:
        """
        Terminate the sandbox.
        """
        if self.started:
            await self.runtime.terminate()
            self.started = False
