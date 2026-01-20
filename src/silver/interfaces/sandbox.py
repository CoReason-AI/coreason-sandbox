# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel


class FileReference(BaseModel):
    """Represents a reference to a file, which could be a local path or a remote URL."""

    # This is a placeholder for now. In a real implementation, this would
    # likely be a more complex type, e.g., a discriminated union of
    # LocalFile, S3File, etc.
    uri: str


class ExecutionResult(BaseModel):
    """Data model for the result of a code execution in the sandbox."""

    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[FileReference]
    execution_duration: float


class SandboxRuntime(ABC):
    """Abstract base class defining the interface for a sandbox runtime."""

    @abstractmethod
    async def start(self) -> None:
        """Boots the environment."""
        # This is an abstract method, so it should not be called directly.
        # It is meant to be overridden by subclasses.
        pass  # pragma: no cover

    @abstractmethod
    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:
        """Runs a script and captures the output."""
        # This is an abstract method, so it should not be called directly.
        # It is meant to be overridden by subclasses.
        pass  # pragma: no cover

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> None:
        """Injects a file into the sandbox."""
        # This is an abstract method, so it should not be called directly.
        # It is meant to be overridden by subclasses.
        pass  # pragma: no cover

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> None:
        """Retrieves a file from the sandbox."""
        # This is an abstract method, so it should not be called directly.
        # It is meant to be overridden by subclasses.
        pass  # pragma: no cover

    @abstractmethod
    async def terminate(self) -> None:
        """Kills the environment and cleans up."""
        # This is an abstract method, so it should not be called directly.
        # It is meant to be overridden by subclasses.
        pass  # pragma: no cover
