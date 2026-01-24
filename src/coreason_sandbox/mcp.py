import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from loguru import logger

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.factory import SandboxFactory
from coreason_sandbox.runtime import SandboxRuntime
from coreason_sandbox.utils.veritas import VeritasIntegrator


@dataclass
class Session:
    runtime: SandboxRuntime
    last_accessed: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    active: bool = True


class SandboxMCP:
    """
    MCP-compliant server logic wrapper for Coreason Sandbox.
    Exposes tools for the Agent.
    Manages multiple sessions with idle timeouts.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.veritas = VeritasIntegrator()
        self.sessions: dict[str, Session] = {}
        self._reaper_task: asyncio.Task[None] | None = None
        self._creation_lock = asyncio.Lock()

    async def _start_reaper_if_needed(self) -> None:
        """Start the background reaper task if it's not running."""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reaper_loop())

    async def _reaper_loop(self) -> None:  # pragma: no cover
        """Background task to cleanup expired sessions."""
        logger.info("Session reaper started")
        try:
            while True:
                await asyncio.sleep(self.config.reaper_interval)
                now = time.time()
                # Create a list of sessions to terminate to avoid modifying dict while iterating
                expired_ids = [
                    sid
                    for sid, session in self.sessions.items()
                    if now - session.last_accessed > self.config.idle_timeout
                ]

                for sid in expired_ids:
                    logger.info(f"Session {sid} expired. Terminating.")
                    session = self.sessions.pop(sid, None)
                    if session:
                        async with session.lock:
                            session.active = False
                            try:
                                await session.runtime.terminate()
                            except Exception as e:
                                logger.error(f"Error terminating expired session {sid}: {e}")

        except asyncio.CancelledError:  # pragma: no cover
            logger.info("Session reaper cancelled")  # pragma: no cover
        except Exception as e:  # pragma: no cover
            logger.error(f"Session reaper crashed: {e}")  # pragma: no cover

    async def _get_or_create_session(self, session_id: str) -> Session:
        """
        Retrieve existing session or create a new one.
        Updates last_accessed timestamp.
        Thread-safe against concurrent creation for same ID.
        """
        await self._start_reaper_if_needed()

        # Optimistic check
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_accessed = time.time()
            return session

        async with self._creation_lock:
            # Double-check inside lock
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.last_accessed = time.time()
                return session

            logger.info(f"Creating new session: {session_id}")
            runtime = SandboxFactory.get_runtime(self.config)

            # Start the runtime immediately
            await runtime.start()

            session = Session(runtime=runtime, last_accessed=time.time())
            self.sessions[session_id] = session
            return session

    async def execute_code(
        self, session_id: str, language: Literal["python", "bash", "r"], code: str
    ) -> dict[str, str | int | float | list[dict[str, Any]]]:
        """
        Execute code in the sandbox for the given session.
        Retries if session is terminated during acquisition.
        """
        while True:
            session = await self._get_or_create_session(session_id)

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
        while True:
            session = await self._get_or_create_session(session_id)

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
        while True:
            session = await self._get_or_create_session(session_id)

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
        if self._reaper_task and not self._reaper_task.done():
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass
            self._reaper_task = None

        logger.info(f"Shutting down MCP. Terminating {len(self.sessions)} sessions.")

        # Snapshot items to allow modification/async issues
        sessions_to_close = list(self.sessions.values())
        self.sessions.clear()

        for session in sessions_to_close:
            try:
                async with session.lock:
                    session.active = False
                    await session.runtime.terminate()
            except Exception as e:
                logger.error(f"Error terminating session during shutdown: {e}")
