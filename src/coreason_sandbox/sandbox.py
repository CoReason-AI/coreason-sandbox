# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from pathlib import Path
from typing import Literal, Optional

import anyio
import httpx

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.factory import SandboxFactory
from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.runtime import SandboxRuntime


class SandboxAsync:
    """Async-native Sandbox Service (The Core).

    Handles all logic and lifecycle management asynchronously.
    """

    def __init__(
        self,
        config: SandboxConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        """Initializes the SandboxAsync service.

        Args:
            config: Configuration for the sandbox.
            client: Optional httpx.AsyncClient for connection pooling.
        """
        self.config = config or SandboxConfig()
        self._internal_client = client is None
        self._client = client or httpx.AsyncClient()
        self.runtime: SandboxRuntime = SandboxFactory.get_runtime(self.config)

    async def __aenter__(self) -> "SandboxAsync":
        """Starts the sandbox environment."""
        await self.runtime.start()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Terminates the sandbox environment and cleans up resources."""
        await self.runtime.terminate()
        if self._internal_client:
            await self._client.aclose()

    async def execute(
        self, code: str, language: Literal["python", "bash", "r"] = "python"
    ) -> ExecutionResult:
        """Executes code in the sandbox.

        Args:
            code: The source code to execute.
            language: The programming language (default: 'python').

        Returns:
            ExecutionResult: The result of the execution.
        """
        return await self.runtime.execute(code, language)

    async def upload(self, local_path: Path, remote_path: str) -> None:
        """Uploads a file to the sandbox.

        Args:
            local_path: Path to the local file.
            remote_path: Destination path in the sandbox.
        """
        await self.runtime.upload(local_path, remote_path)

    async def download(self, remote_path: str, local_path: Path) -> None:
        """Downloads a file from the sandbox.

        Args:
            remote_path: Path to the file in the sandbox.
            local_path: Destination path on the host.
        """
        await self.runtime.download(remote_path, local_path)

    async def install_package(self, package_name: str) -> None:
        """Installs a package in the sandbox.

        Args:
            package_name: The name of the package to install.
        """
        await self.runtime.install_package(package_name)

    async def list_files(self, path: str = ".") -> list[str]:
        """Lists files in the sandbox.

        Args:
            path: The directory path to list.

        Returns:
            list[str]: A list of filenames.
        """
        return await self.runtime.list_files(path)


class Sandbox:
    """Sync Facade for SandboxAsync (The Facade).

    Wraps SandboxAsync and executes methods via anyio.run.
    """

    def __init__(
        self,
        config: SandboxConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        """Initializes the Sandbox facade.

        Args:
            config: Configuration for the sandbox.
            client: Optional httpx.AsyncClient.
        """
        self._async = SandboxAsync(config, client)

    def __enter__(self) -> "Sandbox":
        """Context entry point."""
        # We don't start the runtime here because we need an event loop to run start().
        # But anyio.run creates a loop.
        # However, if we use context manager, we expect the loop to run inside the block?
        # No, the pattern "with Service() as svc:" is synchronous.
        # It means we should run __aenter__ synchronously.
        anyio.run(self._async.__aenter__)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context exit point."""
        anyio.run(self._async.__aexit__, exc_type, exc_val, exc_tb)

    def execute(
        self, code: str, language: Literal["python", "bash", "r"] = "python"
    ) -> ExecutionResult:
        """Executes code in the sandbox synchronously.

        Args:
            code: The source code to execute.
            language: The programming language.

        Returns:
            ExecutionResult: The result of the execution.
        """
        return anyio.run(self._async.execute, code, language)

    def upload(self, local_path: Path, remote_path: str) -> None:
        """Uploads a file to the sandbox synchronously.

        Args:
            local_path: Path to the local file.
            remote_path: Destination path in the sandbox.
        """
        anyio.run(self._async.upload, local_path, remote_path)

    def download(self, remote_path: str, local_path: Path) -> None:
        """Downloads a file from the sandbox synchronously.

        Args:
            remote_path: Path to the file in the sandbox.
            local_path: Destination path on the host.
        """
        anyio.run(self._async.download, remote_path, local_path)

    def install_package(self, package_name: str) -> None:
        """Installs a package in the sandbox synchronously.

        Args:
            package_name: The name of the package to install.
        """
        anyio.run(self._async.install_package, package_name)

    def list_files(self, path: str = ".") -> list[str]:
        """Lists files in the sandbox synchronously.

        Args:
            path: The directory path to list.

        Returns:
            list[str]: A list of filenames.
        """
        return anyio.run(self._async.list_files, path)
