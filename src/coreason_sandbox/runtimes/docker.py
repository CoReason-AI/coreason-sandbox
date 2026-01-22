from pathlib import Path
from typing import Literal

from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.runtime import SandboxRuntime


class DockerRuntime(SandboxRuntime):
    """
    Docker-based implementation of the SandboxRuntime.
    """

    async def start(self) -> None:
        raise NotImplementedError  # pragma: no cover

    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:
        raise NotImplementedError  # pragma: no cover

    async def upload(self, local_path: Path, remote_path: str) -> None:
        raise NotImplementedError  # pragma: no cover

    async def download(self, remote_path: str, local_path: Path) -> None:
        raise NotImplementedError  # pragma: no cover

    async def terminate(self) -> None:
        raise NotImplementedError  # pragma: no cover
