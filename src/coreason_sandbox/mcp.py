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
from typing import Any, Literal

from loguru import logger

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.session_manager import Session, SessionManager
from coreason_sandbox.utils.vault import VaultIntegrator
from coreason_sandbox.utils.veritas import VeritasIntegrator


class SandboxMCP:
    """
    MCP-compliant server logic wrapper for Coreason Sandbox.
    Exposes tools for the Agent.
    Delegates session lifecycle management to SessionManager.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()

        # Vault Integration
        self.vault = VaultIntegrator()
        self._hydrate_config_from_vault()

        self.veritas = VeritasIntegrator()
        self.session_manager = SessionManager(self.config)

    def _hydrate_config_from_vault(self) -> None:
        """
        Fetch secrets from Vault and update config if found.
        """
        secrets_map = {
            "e2b_api_key": "E2B_API_KEY",
            "s3_access_key": "S3_ACCESS_KEY",
            "s3_secret_key": "S3_SECRET_KEY",
        }

        for config_field, vault_key in secrets_map.items():
            secret = self.vault.get_secret(vault_key)
            if secret:
                setattr(self.config, config_field, secret)

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

    async def execute_code(
        self, session_id: str, language: Literal["python", "bash", "r"], code: str
    ) -> dict[str, str | int | float | list[dict[str, Any]]]:
        """
        Execute code in the sandbox for the given session.
        Retries if session is terminated during acquisition.
        """
        if not session_id:
            raise ValueError("Session ID is required")

        while True:
            session = await self.session_manager.get_or_create_session(session_id)

            async with session.lock:
                if not session.active:
                    # Session was reaped while we were waiting for lock or just before
                    logger.warning(f"Session {session_id} inactive/reaped. Retrying creation.")
                    continue

                # Veritas Audit Log
                await self.veritas.log_pre_execution(code, language)

                result = await session.runtime.execute(code, language)

                # Update access time after execution
                session.last_accessed = time.time()
                break

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

    async def install_package(self, session_id: str, package_name: str) -> str:
        """
        Install a package in the sandbox session.
        """
        if not session_id:
            raise ValueError("Session ID is required")

        while True:
            session = await self.session_manager.get_or_create_session(session_id)

            async with session.lock:
                if not session.active:
                    continue

                await session.runtime.install_package(package_name)
                session.last_accessed = time.time()
                break

        return f"Package {package_name} installed successfully."

    async def list_files(self, session_id: str, path: str = ".") -> list[str]:
        """
        List files in the sandbox session directory.
        """
        if not session_id:
            raise ValueError("Session ID is required")

        while True:
            session = await self.session_manager.get_or_create_session(session_id)

            async with session.lock:
                if not session.active:
                    continue

                files = await session.runtime.list_files(path)
                session.last_accessed = time.time()
                break

        return files

    async def shutdown(self) -> None:
        """
        Terminate all sessions and stop the reaper.
        """
        await self.session_manager.shutdown()
