# tests/test_smoke.py

def test_imports():
    """
    A simple smoke test to ensure the core components of the new
    scaffolding are importable.
    """
    try:
        from coreason_sandbox import (
            SandboxRuntime,
            ExecutionResult,
            FileReference
        )
    except ImportError as e:
        assert False, f"Failed to import core components: {e}"

    assert True
