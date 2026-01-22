# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

def test_import_coreason_sandbox_package():
    """Tests that the main application package is importable."""
    try:
        import coreason_sandbox
        from coreason_sandbox.models.models import ExecutionResult
        from coreason_sandbox.runtime.base import SandboxRuntime
    except ImportError as e:
        assert False, f"Failed to import from the 'coreason_sandbox' package: {e}"
