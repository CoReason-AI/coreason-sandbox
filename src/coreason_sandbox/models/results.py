# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from typing import List, Optional

from pydantic import BaseModel


class FileReference(BaseModel):
    path: str
    url: Optional[str] = None
    content: Optional[bytes] = None


class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[FileReference]
    execution_duration: float
