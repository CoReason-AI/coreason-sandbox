from unittest.mock import MagicMock, patch

from coreason_sandbox.integrations.vault import VaultIntegrator


class MockVaultClient:
    def get_secret(self, key: str) -> str | None:
        if key == "EXISTING_KEY":
            return "secret_value"
        return None


def test_vault_integrator_with_client() -> None:
    client = MockVaultClient()
    integrator = VaultIntegrator(client)

    assert integrator.get_secret("EXISTING_KEY") == "secret_value"
    assert integrator.get_secret("MISSING_KEY") is None


def test_vault_settings_source() -> None:
    """Test that VaultSettingsSource correctly loads secrets into Config."""
    from coreason_sandbox.config import SandboxConfig

    # Mock VaultIntegrator to return secrets
    mock_vault = MagicMock()
    mock_vault.get_secret.side_effect = lambda k: "vault_e2b" if k == "E2B_API_KEY" else None

    # Patch VaultIntegrator in config module where Source uses it
    with patch("coreason_sandbox.config.VaultIntegrator", return_value=mock_vault):
        # We need to manually instantiate Source or rely on Pydantic loading it
        # Relying on Pydantic loading:
        config = SandboxConfig()
        assert config.e2b_api_key == "vault_e2b"

        # Verify it called the vault
        mock_vault.get_secret.assert_any_call("E2B_API_KEY")


def test_vault_integrator_no_client_fallback() -> None:
    # Ensure no coreason_vault import
    with patch.dict("sys.modules", {"coreason_vault": None}):
        integrator = VaultIntegrator()
        assert integrator.client is None
        assert integrator.get_secret("ANY") is None


def test_vault_integrator_auto_import() -> None:
    # Simulate coreason_vault existing
    mock_module = MagicMock()
    mock_client_class = MagicMock()
    mock_module.VaultClient = mock_client_class

    with patch.dict("sys.modules", {"coreason_vault": mock_module}):
        integrator = VaultIntegrator()
        assert integrator.client is not None
        mock_client_class.assert_called_once()


def test_vault_integrator_client_exception() -> None:
    mock_client = MagicMock()
    mock_client.get_secret.side_effect = Exception("Connection failed")

    integrator = VaultIntegrator(mock_client)

    # Should catch exception and return None
    result = integrator.get_secret("KEY")
    assert result is None
