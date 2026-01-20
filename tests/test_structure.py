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
This test module verifies the integrity of the project's structure after the
Medallion architecture refactoring. It ensures that the packages are correctly
installed and the core components are importable.
"""


def test_import_coreason_sandbox_package():
    """
    Tests that the main application package ('gold' layer) is importable.
    """
    try:
        import coreason_sandbox
    except ImportError:
        assert False, "Failed to import the 'coreason_sandbox' package."


def test_import_silver_interfaces():
    """
    Tests that the shared interfaces ('silver' layer) are importable.
    """
    try:
        from silver.interfaces.sandbox import ExecutionResult, SandboxRuntime
    except ImportError:
        assert False, "Failed to import from the 'silver.interfaces' module."
