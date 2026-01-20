from silver.interfaces import SandboxRuntime, ExecutionResult
from pathlib import Path
from typing import Literal

class E2BRuntime(SandboxRuntime):
    async def start(self) -> None: pass
    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult: pass
    async def upload(self, local_path: Path, remote_path: str) -> None: pass
    async def download(self, remote_path: str, local_path: Path) -> None: pass
    async def terminate(self) -> None: pass
