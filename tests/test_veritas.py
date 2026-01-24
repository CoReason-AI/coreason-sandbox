from typing import Any
from unittest.mock import patch

import pytest

from coreason_sandbox.utils.veritas import VeritasIntegrator


@pytest.fixture
def mock_ier_logger() -> Any:
    with patch("coreason_sandbox.utils.veritas.IERLogger") as mock:
        yield mock


@pytest.mark.asyncio
async def test_veritas_integration_success(mock_ier_logger: Any) -> None:
    integrator = VeritasIntegrator()
    assert integrator.enabled is True

    code = "print('hello')"
    code_hash = await integrator.log_pre_execution(code, "python")

    assert code_hash == "96f43d529af3430cb6b0e2c02f6b38ef1a121e8a31d2d09a3ebb716f2f35c9de"  # sha256 of "print('hello')"

    mock_ier_logger.return_value.log_event.assert_called_once()
    args, kwargs = mock_ier_logger.return_value.log_event.call_args
    assert kwargs["event_type"] == "SANDBOX_EXECUTION_START"
    assert kwargs["details"]["code_hash"] == code_hash
    assert kwargs["details"]["language"] == "python"


@pytest.mark.asyncio
async def test_veritas_disabled() -> None:
    with patch("coreason_sandbox.utils.veritas.IERLogger", None):
        integrator = VeritasIntegrator()
        assert integrator.enabled is False

        code_hash = await integrator.log_pre_execution("code", "python")
        assert code_hash is not None  # Still returns hash


@pytest.mark.asyncio
async def test_veritas_init_exception() -> None:
    with patch("coreason_sandbox.utils.veritas.IERLogger") as mock:
        mock.side_effect = Exception("Init failed")
        integrator = VeritasIntegrator()
        assert integrator.enabled is False


@pytest.mark.asyncio
async def test_veritas_log_exception(mock_ier_logger: Any) -> None:
    mock_ier_logger.return_value.log_event.side_effect = Exception("Log failed")
    integrator = VeritasIntegrator()
    assert integrator.enabled is True

    # Should not raise exception
    await integrator.log_pre_execution("code", "python")
