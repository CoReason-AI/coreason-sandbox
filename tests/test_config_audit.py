from unittest.mock import MagicMock, patch

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.mcp import SandboxMCP


def test_audit_logging_disabled() -> None:
    """Test initializing SandboxMCP with audit logging disabled."""
    config = SandboxConfig(enable_audit_logging=False)
    mcp = SandboxMCP(config)
    assert mcp.veritas.enabled is False


def test_audit_logging_enabled_mock() -> None:
    """Test initializing SandboxMCP with audit logging enabled (and mocked library)."""
    # Mock IERLogger to be present
    mock_module = MagicMock()
    mock_logger_class = MagicMock()
    mock_module.IERLogger = mock_logger_class

    with patch.dict("sys.modules", {"coreason_veritas.auditor": mock_module}):
        # Need to re-import or patch where it's used
        with patch("coreason_sandbox.integrations.veritas.IERLogger", mock_logger_class):
            config = SandboxConfig(enable_audit_logging=True)
            mcp = SandboxMCP(config)
            assert mcp.veritas.enabled is True
            mock_logger_class.assert_called()


def test_audit_logging_enabled_but_missing_lib() -> None:
    """Test enabled in config but library missing -> disabled."""
    # Ensure import fails or IERLogger is None
    with patch("coreason_sandbox.integrations.veritas.IERLogger", None):
        config = SandboxConfig(enable_audit_logging=True)
        mcp = SandboxMCP(config)
        assert mcp.veritas.enabled is False
