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
from typing import Literal

from coreason_sandbox.models.models import ExecutionResult


class SandboxRuntime(ABC):
    """Abstract base class defining the contract for a sandbox runtime environment."""

    @abstractmethod
    async def start(self) -> None:
        """Boot the environment."""
        pass  # pragma: no cover

    @abstractmethod
    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:
        """Run script and capture output."""
        pass  # pragma: no cover

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> None:
        """Inject file."""
        pass  # pragma: no cover

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> None:
        """Retrieve file."""
        pass  # pragma: no cover

    @abstractmethod
    async def terminate(self) -> None:
        """Kill and cleanup."""
        pass  # pragma: no cover
