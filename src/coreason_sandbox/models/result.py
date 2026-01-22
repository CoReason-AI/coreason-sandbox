from pydantic import BaseModel
from typing import List, Any

# NOTE: FileReference is part of a future AUC (AUC-7: Artifact Manager).
# Using 'Any' as a placeholder to satisfy the current interface requirements.
FileReference = Any

class ExecutionResult(BaseModel):
    """
    A standardized data transfer object for code execution results.

    Attributes:
        stdout: The standard output from the execution.
        stderr: The standard error from the execution.
        exit_code: The exit code of the process.
        artifacts: A list of references to files created during execution.
        execution_duration: The time taken for the code to execute, in seconds.
    """
    stdout: str
    stderr: str
    exit_code: int
    artifacts: List[FileReference] = []
    execution_duration: float
