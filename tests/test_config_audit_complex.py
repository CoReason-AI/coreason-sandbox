from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.mcp import SandboxMCP
from coreason_sandbox.utils.veritas import VeritasIntegrator


@pytest.fixture
def mock_ier_logger() -> Any:
    mock_module = MagicMock()
    mock_logger_class = MagicMock()
    mock_module.IERLogger = mock_logger_class

    with patch.dict("sys.modules", {"coreason_veritas.auditor": mock_module}):
        with patch("coreason_sandbox.utils.veritas.IERLogger", mock_logger_class):
            yield mock_logger_class


def test_veritas_init_failure_graceful_degradation(mock_ier_logger: Any) -> None:
    """
    Test Case E: VeritasIntegrator initialization failure.
    If IERLogger raises an exception during init (e.g. connection error),
    it should catch it and disable itself.
    """
    mock_ier_logger.side_effect = Exception("Connection Refused to OTLP")

    # Init shouldn't raise
    veritas = VeritasIntegrator(enabled=True)

    assert veritas.enabled is False
    assert veritas.logger is None  # Should be None if init failed


@pytest.mark.asyncio
async def test_veritas_log_runtime_failure_non_blocking(mock_ier_logger: Any) -> None:
    """
    Test 2 (Audit Log Failure):
    If log_event raises an exception, it should be logged but NOT stop execution.
    """
    mock_instance = AsyncMock()  # log_event is awaited
    mock_ier_logger.return_value = mock_instance
    mock_instance.log_event.side_effect = Exception("Timeout logging event")

    veritas = VeritasIntegrator(enabled=True)
    assert veritas.enabled is True

    # Should not raise exception
    code_hash = await veritas.log_pre_execution("print('hello')", "python")

    # Hash should still be computed
    assert code_hash is not None
    mock_instance.log_event.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_integration_disabled_lifecycle() -> None:
    """
    Test 3 (Integration Lifecycle):
    Verify that when enabled=False, execution proceeds without attempting to log.
    """
    config = SandboxConfig(enable_audit_logging=False)

    # Mock SessionManager and Runtime to avoid real Docker/E2B calls
    with patch("coreason_sandbox.mcp.SessionManager") as mock_sm_cls:
        mock_sm = mock_sm_cls.return_value

        # Make get_or_create_session return an awaitable mock
        mock_session = MagicMock()
        mock_sm.get_or_create_session = AsyncMock(return_value=mock_session)

        # Async context manager mock for session.lock
        mock_session.lock.__aenter__ = AsyncMock(return_value=None)
        mock_session.lock.__aexit__ = AsyncMock(return_value=None)
        mock_session.active = True

        # Mock runtime execution result (execute is async)
        mock_result = MagicMock()
        mock_result.stdout = "OK"
        mock_result.stderr = ""
        mock_result.exit_code = 0
        mock_result.execution_duration = 0.1
        mock_result.artifacts = []
        mock_session.runtime.execute = AsyncMock(return_value=mock_result)

        mcp = SandboxMCP(config)
        assert mcp.veritas.enabled is False

        # Execute
        result = await mcp.execute_code("sess_1", "python", "print('test')")

        assert result["stdout"] == "OK"
