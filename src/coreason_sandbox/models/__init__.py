# src/coreason_sandbox/models/__init__.py

"""
Data models for the sandbox environment.
"""

from .files import FileReference
from .result import ExecutionResult

__all__ = ["ExecutionResult", "FileReference"]
