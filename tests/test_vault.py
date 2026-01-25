from unittest.mock import MagicMock, patch

import pytest
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.mcp import SandboxMCP
from coreason_sandbox.utils.vault import VaultIntegrator


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

    # Verify warning logged (mock logger?) - loguru is used.
    # We trust loguru, but code coverage just needs the line executed.


@pytest.mark.asyncio
async def test_mcp_hydration() -> None:
    # Mock VaultIntegrator to return specific secrets
    mock_vault = MagicMock()
    mock_vault.get_secret.side_effect = lambda k: f"vault_{k}" if k in ["E2B_API_KEY", "S3_ACCESS_KEY"] else None

    with patch("coreason_sandbox.mcp.VaultIntegrator", return_value=mock_vault):
        config = SandboxConfig()
        # Pre-set some values to ensure override
        config.e2b_api_key = "original_key"

        mcp = SandboxMCP(config)

        # Verify hydration
        assert mcp.config.e2b_api_key == "vault_E2B_API_KEY"
        assert mcp.config.s3_access_key == "vault_S3_ACCESS_KEY"
        assert mcp.config.s3_secret_key is None

        mock_vault.get_secret.assert_any_call("E2B_API_KEY")


@pytest.mark.asyncio
async def test_mcp_hydration_no_secrets() -> None:
    mock_vault = MagicMock()
    mock_vault.get_secret.return_value = None

    with patch("coreason_sandbox.mcp.VaultIntegrator", return_value=mock_vault):
        config = SandboxConfig()
        config.e2b_api_key = "original_key"

        mcp = SandboxMCP(config)

        # Should remain original
        assert mcp.config.e2b_api_key == "original_key"
