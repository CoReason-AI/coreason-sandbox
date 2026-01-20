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
    """Represents a reference to a file artifact."""
    # This is a placeholder for now, will be fleshed out in a future AUC.
    # For example, it could contain a URL to S3, a base64 string, etc.
    name: str
    path: str


class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[FileReference]
    execution_duration: float


class SandboxRuntime(ABC):
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
