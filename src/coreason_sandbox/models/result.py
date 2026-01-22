# src/coreason_sandbox/models/result.py
from typing import List
from pydantic import BaseModel
from .files import FileReference

class ExecutionResult(BaseModel):
    """
    Represents the result of a code execution in the sandbox.
    """
    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[FileReference]
    execution_duration: float
