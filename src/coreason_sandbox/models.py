# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from pydantic import BaseModel


class FileReference(BaseModel):
    """Represents a file artifact generated or manipulated within the sandbox.

    Attributes:
        filename: The original name of the file.
        path: The path to the file (local or remote).
        content_type: The MIME type of the file content.
        size_bytes: The size of the file in bytes.
        url: A URL (e.g., S3 signed URL or data URI) to access the file content.
    """

    filename: str
    path: str
    content_type: str | None = None
    size_bytes: int | None = None
    url: str | None = None


class ExecutionResult(BaseModel):
    """Represents the result of a code execution within the sandbox.

    Attributes:
        stdout: Standard output captured from the execution.
        stderr: Standard error captured from the execution.
        exit_code: The exit code of the process (0 for success).
        artifacts: A list of file artifacts generated during execution.
        execution_duration: The duration of the execution in seconds.
    """

    stdout: str
    stderr: str
    exit_code: int
    artifacts: list[FileReference]
    execution_duration: float
