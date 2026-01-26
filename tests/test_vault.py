from typing import Any
from unittest.mock import patch, MagicMock
import pytest
from coreason_sandbox.integrations.vault import VaultIntegrator


def test_vault_integrator_env_var_fallback() -> None:
    """Test fetching from direct env var."""
    with patch.dict("os.environ", {"API_KEY": "secret_value"}):
        integrator = VaultIntegrator()
        assert integrator.get_secret("API_KEY") == "secret_value"


def test_vault_integrator_prefix_fallback() -> None:
    """Test fetching from prefixed env var."""
    with patch.dict("os.environ", {"COREASON_SANDBOX_API_KEY": "secret_value"}):
        integrator = VaultIntegrator()
        assert integrator.get_secret("API_KEY") == "secret_value"


def test_vault_integrator_missing() -> None:
    """Test missing secret returns None."""
    integrator = VaultIntegrator()
    assert integrator.get_secret("MISSING_KEY") is None


def test_vault_integrator_init_ignore_client() -> None:
    """Test that init accepts arguments but ignores them."""
    client = MagicMock()
    integrator = VaultIntegrator(client)
    # No assertion on internal state, just that it doesn't crash
    assert integrator.get_secret("MISSING") is None
