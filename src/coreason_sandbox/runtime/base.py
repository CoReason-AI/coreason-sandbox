# src/coreason_sandbox/runtime/base.py
from abc import ABC, abstractmethod
from typing import Literal
from pathlib import Path
from ..models import ExecutionResult

class SandboxRuntime(ABC):
    """
    Abstract base class defining the interface for a sandbox runtime.
    This class adheres to the Strategy Pattern, allowing for interchangeable
    runtime implementations (e.g., Docker, E2B).
    """

    @abstractmethod
    async def start(self) -> None:  # pragma: no cover
        """Boot the environment."""
        pass

    @abstractmethod
    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:  # pragma: no cover
        """Run script and capture output."""
        pass

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> None:  # pragma: no cover
        """Inject file."""
        pass

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> None:  # pragma: no cover
        """Retrieve file."""
        pass

    @abstractmethod
    async def terminate(self) -> None:  # pragma: no cover
        """Kill and cleanup."""
        pass
