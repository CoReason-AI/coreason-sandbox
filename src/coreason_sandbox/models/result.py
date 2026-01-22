# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from typing import List
from pydantic import BaseModel, Field

class FileReference(BaseModel):
    """Represents a reference to a file artifact."""
    filename: str = Field(..., description="The name of the file.")
    url: str = Field(..., description="A temporary, signed URL to access the file.")


class ExecutionResult(BaseModel):
    """
    Encapsulates the output and artifacts from a code execution request.
    """
    stdout: str = Field(..., description="The standard output stream of the execution.")
    stderr: str = Field(..., description="The standard error stream, if any.")
    exit_code: int = Field(..., description="The exit code of the process.")
    artifacts: List[FileReference] = Field(
        default_factory=list,
        description="A list of files generated and captured during execution."
    )
    execution_duration: float = Field(
        ...,
        description="The total time in seconds taken for the code to execute."
    )
