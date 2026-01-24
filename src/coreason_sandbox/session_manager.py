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
from dataclasses import dataclass, field

from loguru import logger

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.factory import SandboxFactory
from coreason_sandbox.runtime import SandboxRuntime


@dataclass
class Session:
    runtime: SandboxRuntime
    last_accessed: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    active: bool = True


class SessionManager:
    """
    Manages the lifecycle of sandbox sessions.
    Handles creation, caching, and automatic cleanup of idle sessions.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.sessions: dict[str, Session] = {}
        self._reaper_task: asyncio.Task[None] | None = None
        self._creation_lock = asyncio.Lock()

    async def get_or_create_session(self, session_id: str) -> Session:
        """
        Retrieve existing session or create a new one.
        Updates last_accessed timestamp.
        Thread-safe against concurrent creation for same ID.
        """
        if not session_id:
            raise ValueError("Session ID is required")

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

    async def _start_reaper_if_needed(self) -> None:
        """Start the background reaper task if it's not running."""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reaper_loop())

    async def _reaper_loop(self) -> None:
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

        except asyncio.CancelledError:
            logger.info("Session reaper cancelled")
        except Exception as e:
            logger.error(f"Session reaper crashed: {e}")

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

        logger.info(f"Shutting down SessionManager. Terminating {len(self.sessions)} sessions.")

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
