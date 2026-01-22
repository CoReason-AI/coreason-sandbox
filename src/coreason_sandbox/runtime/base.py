from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from coreason_sandbox.models.result import ExecutionResult


class SandboxRuntime(ABC):
    """
    An abstract base class that defines the standard interface for a sandbox runtime.

    This class adheres to the Strategy Pattern, allowing for different runtime
    implementations (e.g., Docker, E2B) to be used interchangeably.
    """

    @abstractmethod
    async def start(self) -> None:  # pragma: no cover
        """
        Boots the sandboxed environment, preparing it for execution.
        """
        pass

    @abstractmethod
    async def execute(  # pragma: no cover
        self, code: str, language: Literal["python", "bash", "r"]
    ) -> ExecutionResult:
        """
        Executes a script within the sandbox and captures the output.

        Args:
            code: The source code to execute.
            language: The programming language of the script.

        Returns:
            An ExecutionResult object containing the output and metadata.
        """
        pass

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> None:  # pragma: no cover
        """
        Uploads a file from the local filesystem to the sandbox.

        Args:
            local_path: The path to the local file.
            remote_path: The destination path within the sandbox.
        """
        pass

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> None:  # pragma: no cover
        """
        Downloads a file from the sandbox to the local filesystem.

        Args:
            remote_path: The path to the file within the sandbox.
            local_path: The destination path on the local filesystem.
        """
        pass

    @abstractmethod
    async def terminate(self) -> None:  # pragma: no cover
        """
        Terminates and cleans up the sandboxed environment, destroying all data.
        """
        pass
