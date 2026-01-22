# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""Abstract interface for a secure code execution sandbox."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from coreason_sandbox.models.results import ExecutionResult


class SandboxRuntime(ABC):
    """A contract for runtime engines that can execute code in an isolated environment."""

    @abstractmethod
    async def start(self) -> None:
        """Boots the environment, preparing it for execution."""
        # pragma: no cover
        pass

    @abstractmethod
    async def execute(
        self, code: str, language: Literal["python", "bash", "r"]
    ) -> ExecutionResult:
        """Runs a script and captures its output."""
        # pragma: no cover
        pass

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> None:
        """Injects a file into the sandbox's filesystem."""
        # pragma: no cover
        pass

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> None:
        """Retrieves a file from the sandbox."""
        # pragma: no cover
        pass

    @abstractmethod
    async def terminate(self) -> None:
        """Kills the environment and cleans up all resources."""
        # pragma: no cover
        pass
