# Copyright (c) 2025 CoReason, Inc.
"""Interfaces and data models for the sandbox."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Literal
from pydantic import BaseModel

class FileReference(BaseModel):
    name: str
    path: str
    size: int

class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[FileReference]
    execution_duration: float

class SandboxRuntime(ABC):
    @abstractmethod
    async def start(self) -> None: pass
    @abstractmethod
    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult: pass
    @abstractmethod
    async def upload(self, local_path: Path, remote_path: str) -> None: pass
    @abstractmethod
    async def download(self, remote_path: str, local_path: Path) -> None: pass
    @abstractmethod
    async def terminate(self) -> None: pass
