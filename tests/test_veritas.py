from unittest.mock import patch

import pytest
from coreason_sandbox.integrations.veritas import VeritasIntegrator


@pytest.mark.asyncio
async def test_veritas_integration_success() -> None:
    """Test successful logging to stdout."""
    # We patch loguru to verify it was called
    with patch("coreason_sandbox.integrations.veritas.logger") as mock_logger:
        integrator = VeritasIntegrator(enabled=True)
        code_hash = await integrator.log_pre_execution("print('hello')", "python")

        # Verify hash format (sha256 hex)
        assert len(code_hash) == 64

        # Verify logger was called
        mock_logger.info.assert_called()
        args, _ = mock_logger.info.call_args
        assert "AUDIT: Executing python code" in args[0]


@pytest.mark.asyncio
async def test_veritas_disabled() -> None:
    """Test when disabled."""
    with patch("coreason_sandbox.integrations.veritas.logger") as mock_logger:
        integrator = VeritasIntegrator(enabled=False)
        code_hash = await integrator.log_pre_execution("code", "python")

        assert len(code_hash) == 64
        # Verify logger NOT called for audit
        # Note: __init__ logs nothing if disabled, log_pre_execution logs nothing if disabled
        # But we need to distinguish which call.
        # Check call count.
        mock_logger.info.assert_not_called()
