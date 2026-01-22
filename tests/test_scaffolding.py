# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

import inspect

from pydantic import BaseModel

from coreason_sandbox import ExecutionResult, FileReference, SandboxRuntime


def test_core_imports():
    """Verify that the core components are importable."""
    assert SandboxRuntime is not None
    assert ExecutionResult is not None
    assert FileReference is not None


def test_sandbox_runtime_is_abc():
    """Verify that SandboxRuntime is an abstract base class."""
    assert inspect.isabstract(SandboxRuntime)


def test_execution_result_is_pydantic_model():
    """Verify that ExecutionResult is a Pydantic BaseModel."""
    assert issubclass(ExecutionResult, BaseModel)


def test_file_reference_is_pydantic_model():
    """Verify that FileReference is a Pydantic BaseModel."""
    assert issubclass(FileReference, BaseModel)


def test_sandbox_runtime_abstract_methods():
    """Verify that SandboxRuntime has the correct abstract methods."""
    expected_methods = {
        "start",
        "execute",
        "upload",
        "download",
        "terminate",
    }
    abstract_methods = SandboxRuntime.__abstractmethods__
    assert abstract_methods == expected_methods

