# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""Data models for execution results and file references."""

from typing import List
from pydantic import BaseModel


class FileReference(BaseModel):
    """Represents a reference to a file artifact."""
    
    name: str
    path: str
    size: int


class ExecutionResult(BaseModel):
    """Represents the result of a code execution in the sandbox."""

    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[FileReference]
    execution_duration: float
