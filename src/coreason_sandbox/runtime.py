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

from coreason_identity.models import UserContext

from coreason_sandbox.models import ExecutionResult


class SandboxRuntime(ABC):
    """
    Abstract base class for sandbox runtimes (e.g., Docker, E2B).
    Follows the Strategy Pattern.
    """

    @abstractmethod
    async def start(self) -> None:
        """Boot the environment.

        Initializes and starts the underlying sandbox environment (e.g., Docker container
        or E2B microVM).

        Raises:
            RuntimeError: If the sandbox fails to start.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def execute(
        self, code: str, language: Literal["python", "bash", "r"], context: UserContext, session_id: str
    ) -> ExecutionResult:
        """Run script and capture output.

        Executes the provided code in the specified language within the sandbox.

        Args:
            code: The source code to execute.
            language: The programming language of the code ('python', 'bash', 'r').
            context: The user context.
            session_id: The session ID.

        Returns:
            ExecutionResult: The result containing stdout, stderr, exit code, and artifacts.

        Raises:
            ValueError: If the language is not supported.
            RuntimeError: If the sandbox is not running or execution fails.
            TimeoutError: If the execution exceeds the configured timeout.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str, context: UserContext, session_id: str) -> None:
        """Inject file into the sandbox.

        Uploads a file from the local filesystem to the sandbox environment.

        Args:
            local_path: The path to the file on the local machine.
            remote_path: The destination path inside the sandbox.
            context: The user context.
            session_id: The session ID.

        Raises:
            FileNotFoundError: If the local file does not exist.
            RuntimeError: If the upload fails or sandbox is not running.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def download(self, remote_path: str, local_path: Path, context: UserContext, session_id: str) -> None:
        """Retrieve file from the sandbox.

        Downloads a file from the sandbox environment to the local filesystem.

        Args:
            remote_path: The path to the file inside the sandbox.
            local_path: The destination path on the local machine.
            context: The user context.
            session_id: The session ID.

        Raises:
            FileNotFoundError: If the remote file does not exist.
            RuntimeError: If the download fails or sandbox is not running.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def install_package(self, package_name: str, context: UserContext, session_id: str) -> None:
        """Install a package dependency.

        Installs a Python package in the sandbox environment.

        Args:
            package_name: The name of the package to install.
            context: The user context.
            session_id: The session ID.

        Raises:
            ValueError: If the package is not allowed by policy.
            RuntimeError: If the installation fails or sandbox is not running.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def list_files(self, path: str, context: UserContext, session_id: str) -> list[str]:
        """List files in the directory.

        Args:
            path: The directory path to list.
            context: The user context.
            session_id: The session ID.

        Returns:
            list[str]: A list of filenames in the directory.

        Raises:
            RuntimeError: If listing fails or sandbox is not running.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def terminate(self) -> None:
        """Kill and cleanup the sandbox environment.

        Stops the sandbox and releases any allocated resources.
        """
        pass  # pragma: no cover
