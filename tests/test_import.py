import pytest

def test_imports():
    """
    Tests that the main components of the package are importable.
    """
    try:
        from coreason_sandbox import ExecutionResult, SandboxRuntime
    except ImportError as e:
        pytest.fail(f"Failed to import core components: {e}")
