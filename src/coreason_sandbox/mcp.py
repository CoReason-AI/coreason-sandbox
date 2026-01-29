# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal

from coreason_identity.models import UserContext
from loguru import logger

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.integrations.veritas import VeritasIntegrator
from coreason_sandbox.session_manager import Session, SessionManager


class SandboxMCP:
    """MCP-compliant server logic wrapper for Coreason Sandbox.

    Exposes tools for the Agent and delegates session lifecycle management to
    SessionManager.
    """

    def __init__(self, config: SandboxConfig | None = None):
        """Initializes the SandboxMCP.

        Args:
            config: Optional configuration object. If not provided, defaults are used.
        """
        self.config = config or SandboxConfig()

        self.veritas = VeritasIntegrator(enabled=self.config.enable_audit_logging)
        self.session_manager = SessionManager(self.config)

    @property
    def sessions(self) -> dict[str, Session]:
        # Expose sessions property for backward compatibility with tests if needed,
        # or just for inspection.
        # However, tests access mcp.sessions directly. I should update tests or expose this.
        # Exposing it is safer for minimal test churn.
        return self.session_manager.sessions

    @property
    def _reaper_task(self) -> asyncio.Task[None] | None:
        # For tests that inspect reaper task
        return self.session_manager._reaper_task

    @asynccontextmanager
    async def _session_scope(self, session_id: str, context: UserContext) -> AsyncIterator[Session]:
        """Context manager to acquire a locked, active session.

        Retries if session is terminated during acquisition (race condition).
        Updates last_accessed time on exit.

        Args:
            session_id: The unique identifier for the session.
            context: The user context for the session.

        Yields:
            Session: An active, locked session.

        Raises:
            ValueError: If session_id is empty.
        """
        if not session_id:
            raise ValueError("Session ID is required")

        while True:
            session = await self.session_manager.get_or_create_session(session_id, context)

            async with session.lock:
                if not session.active:
                    # Session was reaped while we were waiting for lock or just before
                    logger.warning(f"Session {session_id} inactive/reaped. Retrying creation.")
                    continue

                try:
                    yield session
                finally:
                    # Update access time after execution
                    session.last_accessed = time.time()
                break

    async def execute_code(
        self,
        session_id: str,
        language: Literal["python", "bash", "r"],
        code: str,
        context: UserContext,
    ) -> dict[str, str | int | float | list[dict[str, Any]]]:
        """Execute code in the sandbox for the given session.

        Args:
            session_id: The unique identifier for the session.
            language: The programming language to use ('python', 'bash', 'r').
            code: The source code to execute.
            context: The user context.

        Returns:
            dict: A dictionary containing stdout, stderr, exit_code, duration, and artifacts.
        """
        async with self._session_scope(session_id, context) as session:
            # Veritas Audit Log
            await self.veritas.log_pre_execution(code, language)

            logger.info(
                "Executing code in sandbox",
                user_id=context.sub,
                session_id=str(session_id),
            )

            result = await session.runtime.execute(code, language, context, session_id)

        # Convert artifacts to simpler dicts for MCP response if needed
        artifacts_data = [
            {
                "filename": a.filename,
                "url": a.url,
                "content_type": a.content_type,
            }
            for a in result.artifacts
        ]

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "execution_duration": result.execution_duration,
            "artifacts": artifacts_data,
        }

    async def install_package(self, session_id: str, package_name: str, context: UserContext) -> str:
        """Install a package in the sandbox session.

        Args:
            session_id: The unique identifier for the session.
            package_name: The name of the package to install.
            context: The user context.

        Returns:
            str: A success message.
        """
        async with self._session_scope(session_id, context) as session:
            await session.runtime.install_package(package_name, context, session_id)

        return f"Package {package_name} installed successfully."

    async def list_files(self, session_id: str, context: UserContext, path: str = ".") -> list[str]:
        """List files in the sandbox session directory.

        Args:
            session_id: The unique identifier for the session.
            context: The user context.
            path: The directory path to list (default: ".").

        Returns:
            list[str]: A list of filenames.
        """
        async with self._session_scope(session_id, context) as session:
            files = await session.runtime.list_files(path, context, session_id)

        return files

    async def shutdown(self) -> None:
        """Terminate all sessions and stop the reaper.

        Delegates to SessionManager.shutdown().
        """
        await self.session_manager.shutdown()
