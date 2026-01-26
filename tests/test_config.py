from unittest.mock import patch, MagicMock
from coreason_sandbox.config import SandboxConfig, VaultSettingsSource


def test_vault_settings_source_injects_secrets() -> None:
    """Test that VaultSettingsSource hydrates config from env vars (simulated vault)."""
    with patch.dict("os.environ", {"E2B_API_KEY": "secret_key"}):
        config = SandboxConfig()
        assert config.e2b_api_key == "secret_key"


def test_vault_settings_source_ignores_missing() -> None:
    """Test that missing secrets are ignored."""
    # Ensure environment is clean of relevant keys
    with patch.dict("os.environ", {}, clear=True):
        config = SandboxConfig()
        assert config.e2b_api_key is None
