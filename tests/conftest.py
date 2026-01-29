from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from coreason_identity.models import UserContext


@pytest.fixture
def mock_ier_logger() -> Generator[Any, None, None]:
    mock_module = MagicMock()
    mock_logger_class = MagicMock()
    mock_module.IERLogger = mock_logger_class

    with patch.dict("sys.modules", {"coreason_veritas.auditor": mock_module}):
        with patch("coreason_sandbox.integrations.veritas.IERLogger", mock_logger_class):
            yield mock_logger_class


@pytest.fixture
def mock_vault_client() -> Generator[Any, None, None]:
    mock_module = MagicMock()
    mock_client_class = MagicMock()
    mock_module.VaultClient = mock_client_class

    with patch.dict("sys.modules", {"coreason_vault": mock_module}):
        yield mock_client_class


@pytest.fixture
def mock_veritas_integrator() -> Generator[Any, None, None]:
    with patch("coreason_sandbox.mcp.VeritasIntegrator") as mock:
        instance = mock.return_value
        instance.log_pre_execution = MagicMock()
        yield mock


@pytest.fixture
def mock_vault_integrator() -> Generator[Any, None, None]:
    with patch("coreason_sandbox.config.VaultIntegrator") as mock:
        yield mock


@pytest.fixture
def mock_user_context() -> UserContext:
    return UserContext(sub="test-user", email="test@example.com", permissions=["tester"])
