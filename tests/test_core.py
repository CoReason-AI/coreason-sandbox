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
Core tests for the sandbox package structure and API.
"""

def test_package_imports():
    """
    Tests that the core components can be imported from the package.
    """
    from coreason_sandbox import (
        ExecutionResult,
        FileReference,
        SandboxRuntime,
    )
    from pydantic import BaseModel
    from abc import ABC

    assert issubclass(ExecutionResult, BaseModel)
    assert issubclass(FileReference, BaseModel)
    assert issubclass(SandboxRuntime, ABC)
