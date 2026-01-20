# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""
coreason-sandbox
"""

__version__ = "0.1.0"
__author__ = "Gowtham A Rao"
__email__ = "gowtham.rao@coreason.ai"

from .config import SandboxConfig
from .factory import get_runtime
from .models.execution import ExecutionResult, FileReference
from .runtimes.base import SandboxRuntime
from .runtimes.docker import DockerRuntime
from .runtimes.e2b import E2BRuntime

__all__ = [
    "SandboxRuntime",
    "ExecutionResult",
    "FileReference",
    "SandboxConfig",
    "get_runtime",
    "DockerRuntime",
    "E2BRuntime",
]
