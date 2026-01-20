# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

def test_gold_package_importable():
    """
    Tests that the main application package, coreason_sandbox, is importable from its new location in src/gold.
    This is a basic smoke test to ensure the pyproject.toml and the project structure are correctly configured.
    """
    try:
        from coreason_sandbox.main import hello_world
        assert hello_world() == "Hello World!"
    except ImportError as e:
        assert False, f"Failed to import from coreason_sandbox: {e}"

def test_silver_package_importable():
    """
    Tests that the silver package, containing the interfaces, is importable.
    This verifies that the multi-package setup in pyproject.toml is working.
    """
    try:
        from silver.interfaces import SandboxRuntime, ExecutionResult, FileReference
        # Just checking for import errors, no need to instantiate the ABC
        assert issubclass(SandboxRuntime, object)
        assert issubclass(ExecutionResult, object)
        assert issubclass(FileReference, object)
    except ImportError as e:
        assert False, f"Failed to import from silver: {e}"
