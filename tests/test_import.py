# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""Test that the public API is importable."""


def test_imports():
    """Verify that core components can be imported."""
    try:
        from coreason_sandbox import (
            ExecutionResult,
            FileReference,
            SandboxRuntime,
        )
    except ImportError as e:
        assert False, f"Failed to import core components: {e}"

    # Simple assertions to ensure the imported objects are classes
    assert isinstance(SandboxRuntime, type)
    assert isinstance(ExecutionResult, type)
    assert isinstance(FileReference, type)
