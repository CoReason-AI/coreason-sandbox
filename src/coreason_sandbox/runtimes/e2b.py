from pathlib import Path
from typing import Literal

from coreason_sandbox.models.execution import ExecutionResult

from .base import SandboxRuntime

class E2BRuntime(SandboxRuntime):
    async def start(self) -> None:  # pragma: no cover
        pass
    async def execute(
        self, code: str, language: Literal["python", "bash", "r"]
    ) -> ExecutionResult:  # pragma: no cover
        pass
    async def upload(self, local_path: Path, remote_path: str) -> None:  # pragma: no cover
        pass
    async def download(self, remote_path: str, local_path: Path) -> None:  # pragma: no cover
        pass
    async def terminate(self) -> None:  # pragma: no cover
        pass
