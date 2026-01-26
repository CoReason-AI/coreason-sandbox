from unittest.mock import patch
from coreason_sandbox.config import SandboxConfig


def test_config_env_var_override() -> None:
    """Test that SandboxConfig reads from standard env vars."""
    # Pydantic reads COREASON_SANDBOX_ prefixed vars
    with patch.dict("os.environ", {"COREASON_SANDBOX_E2B_API_KEY": "secret_key"}):
        config = SandboxConfig()
        assert config.e2b_api_key == "secret_key"


def test_config_defaults() -> None:
    """Test defaults when no env vars are present."""
    with patch.dict("os.environ", {}, clear=True):
        config = SandboxConfig()
        assert config.e2b_api_key is None
        assert config.runtime == "docker"
