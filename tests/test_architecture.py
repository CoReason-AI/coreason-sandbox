# Copyright (c) 2025 CoReason, Inc.
"""Tests to verify the integrity of the Medallion architecture."""

def test_import_silver_interface():
    """Tests that the core SandboxRuntime ABC can be imported from the silver layer."""
    try:
        from silver.interfaces import SandboxRuntime
        assert SandboxRuntime is not None
    except ImportError as e:
        assert False, f"Failed to import SandboxRuntime from silver layer: {e}"

def test_import_gold_application():
    """Tests that the application-level code can be imported from the gold layer."""
    try:
        from coreason_sandbox.factory import get_runtime
        assert get_runtime is not None
    except ImportError as e:
        assert False, f"Failed to import get_runtime from gold layer: {e}"

def test_hello_world():
    """Tests the hello_world function from the main module."""
    from coreason_sandbox.main import hello_world
    assert hello_world() == "Hello World!"

def test_get_runtime_default():
    """Tests that the default runtime is DockerRuntime."""
    from coreason_sandbox.factory import get_runtime
    from coreason_sandbox.runtimes.docker import DockerRuntime
    runtime = get_runtime()
    assert isinstance(runtime, DockerRuntime)
