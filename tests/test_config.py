import os
from unittest import mock

import pytest
from coreason_sandbox.config import SandboxConfig


def test_default_config() -> None:
    """Test that default configuration is correct."""
    config = SandboxConfig()
    assert config.runtime == "docker"


def test_config_from_env() -> None:
    """Test loading configuration from environment variables."""
    with mock.patch.dict(os.environ, {"COREASON_SANDBOX_RUNTIME": "e2b"}):
        config = SandboxConfig()
        assert config.runtime == "e2b"


def test_invalid_runtime_config() -> None:
    """Test that invalid runtime values raise ValidationError."""
    with mock.patch.dict(os.environ, {"COREASON_SANDBOX_RUNTIME": "invalid"}):
        with pytest.raises(ValueError):  # Pydantic raises ValidationError
            SandboxConfig()
