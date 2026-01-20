# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""Tests for the basic scaffolding of the package."""

import pytest

def test_import_runtime_interface():
    """Test that the SandboxRuntime interface can be imported."""
    try:
        from coreason_sandbox import SandboxRuntime
    except ImportError as e:
        pytest.fail(f"Failed to import SandboxRuntime: {e}")

def test_import_execution_models():
    """Test that the execution data models can be imported."""
    try:
        from coreason_sandbox import ExecutionResult, FileReference
    except ImportError as e:
        pytest.fail(f"Failed to import ExecutionResult or FileReference: {e}")
