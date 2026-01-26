import importlib
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import coreason_sandbox.integrations.veritas
import pytest
from coreason_sandbox.artifacts import ArtifactManager

# --- ArtifactManager Tests ---


def test_artifacts_file_not_found() -> None:
    """Test that FileNotFoundError is raised if file doesn't exist."""
    manager = ArtifactManager()
    with pytest.raises(FileNotFoundError):
        manager.process_file(Path("/non/existent/path.txt"), "test.txt")


def test_artifacts_unknown_mimetype(tmp_path: Path) -> None:
    """Test fallback to application/octet-stream for unknown mime types."""
    # Create a dummy file
    f = tmp_path / "test.unknown"
    f.write_text("content")

    manager = ArtifactManager()

    # Force mimetypes.guess_type to return None
    with patch("mimetypes.guess_type", return_value=(None, None)):
        ref = manager.process_file(f, "test.unknown")
        assert ref.content_type == "application/octet-stream"


def test_artifacts_upload_failure(tmp_path: Path) -> None:
    """Test that upload failure is handled gracefully (ignored)."""
    f = tmp_path / "doc.pdf"
    f.write_text("pdf content")

    # Mock storage that raises exception
    mock_storage = MagicMock()
    mock_storage.upload_file.side_effect = Exception("Upload failed")

    manager = ArtifactManager(storage=mock_storage)

    # Should not raise exception
    ref = manager.process_file(f, "doc.pdf")
    assert ref.url is None


# --- Veritas Tests ---


def test_veritas_import_error_simulation() -> None:
    """
    Test behavior when coreason_veritas is missing.
    This requires reloading the module while the dependency is hidden.
    """
    # 1. Hide coreason_veritas from sys.modules
    with patch.dict(sys.modules):
        # Remove if present
        if "coreason_veritas" in sys.modules:
            del sys.modules["coreason_veritas"]
        if "coreason_veritas.auditor" in sys.modules:
            del sys.modules["coreason_veritas.auditor"]

        # Mock __import__ to raise ImportError for this specific package
        real_import = __import__

        def mock_import(
            name: str,
            globals: Any = None,
            locals: Any = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> Any:
            if name == "coreason_veritas.auditor" or name == "coreason_veritas":
                raise ImportError(f"No module named {name}")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=mock_import):
            # Reload the module under test
            importlib.reload(coreason_sandbox.integrations.veritas)

            # Assertions
            # Use getattr to avoid mypy error about IERLogger not being exported
            assert getattr(coreason_sandbox.integrations.veritas, "IERLogger", None) is None
            integrator = coreason_sandbox.integrations.veritas.VeritasIntegrator()
            assert integrator.enabled is False

    # 2. Cleanup: Reload the module again to restore it to original state
    #    (assuming coreason_veritas is actually installed in the env)
    importlib.reload(coreason_sandbox.integrations.veritas)
