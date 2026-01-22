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

from coreason_sandbox.models.result import ExecutionResult


class SandboxRuntime(ABC):
    """
    Abstract base class for a sandbox runtime environment.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Boots the environment, preparing it for code execution.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def execute(
        self, code: str, language: Literal["python", "bash", "r"]
    ) -> ExecutionResult:
        """
        Runs a script within the sandbox and captures the output.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> None:
        """
        Injects a file from the local filesystem into the sandbox.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> None:
        """
        Retrieves a file from the sandbox and saves it locally.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def terminate(self) -> None:
        """
        Kills the environment and performs all necessary cleanup.
        """
        pass  # pragma: no cover
