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
from typing import Literal
from uuid import uuid4

import anyio
import httpx
from loguru import logger
from coreason_identity.models import UserContext

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
        self.session_id = str(uuid4())

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
        self,
        code: str,
        context: UserContext,
        language: Literal["python", "bash", "r"] = "python",
    ) -> ExecutionResult:
        """Executes code in the sandbox.

        Args:
            code: The source code to execute.
            context: The user context.
            language: The programming language (default: 'python').

        Returns:
            ExecutionResult: The result of the execution.
        """
        logger.info(
            "Executing code in sandbox",
            user_id=context.sub,
            session_id=self.session_id,
        )
        return await self.runtime.execute(code, language, context, self.session_id)

    async def upload(self, local_path: Path, remote_path: str, context: UserContext) -> None:
        """Uploads a file to the sandbox.

        Args:
            local_path: Path to the local file.
            remote_path: Destination path in the sandbox.
            context: The user context.
        """
        await self.runtime.upload(local_path, remote_path, context, self.session_id)

    async def download(self, remote_path: str, local_path: Path, context: UserContext) -> None:
        """Downloads a file from the sandbox.

        Args:
            remote_path: Path to the file in the sandbox.
            local_path: Destination path on the host.
            context: The user context.
        """
        await self.runtime.download(remote_path, local_path, context, self.session_id)

    async def install_package(self, package_name: str, context: UserContext) -> None:
        """Installs a package in the sandbox.

        Args:
            package_name: The name of the package to install.
            context: The user context.
        """
        await self.runtime.install_package(package_name, context, self.session_id)

    async def list_files(self, context: UserContext, path: str = ".") -> list[str]:
        """Lists files in the sandbox.

        Args:
            context: The user context.
            path: The directory path to list.

        Returns:
            list[str]: A list of filenames.
        """
        return await self.runtime.list_files(path, context, self.session_id)


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
        anyio.run(self._async.__aenter__)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context exit point."""
        anyio.run(self._async.__aexit__, exc_type, exc_val, exc_tb)

    def execute(
        self,
        code: str,
        context: UserContext,
        language: Literal["python", "bash", "r"] = "python",
    ) -> ExecutionResult:
        """Executes code in the sandbox synchronously.

        Args:
            code: The source code to execute.
            context: The user context.
            language: The programming language.

        Returns:
            ExecutionResult: The result of the execution.
        """
        return anyio.run(self._async.execute, code, context, language)

    def upload(self, local_path: Path, remote_path: str, context: UserContext) -> None:
        """Uploads a file to the sandbox synchronously.

        Args:
            local_path: Path to the local file.
            remote_path: Destination path in the sandbox.
            context: The user context.
        """
        anyio.run(self._async.upload, local_path, remote_path, context)

    def download(self, remote_path: str, local_path: Path, context: UserContext) -> None:
        """Downloads a file from the sandbox synchronously.

        Args:
            remote_path: Path to the file in the sandbox.
            local_path: Destination path on the host.
            context: The user context.
        """
        anyio.run(self._async.download, remote_path, local_path, context)

    def install_package(self, package_name: str, context: UserContext) -> None:
        """Installs a package in the sandbox synchronously.

        Args:
            package_name: The name of the package to install.
            context: The user context.
        """
        anyio.run(self._async.install_package, package_name, context)

    def list_files(self, context: UserContext, path: str = ".") -> list[str]:
        """Lists files in the sandbox synchronously.

        Args:
            context: The user context.
            path: The directory path to list.

        Returns:
            list[str]: A list of filenames.
        """
        return anyio.run(self._async.list_files, context, path)
