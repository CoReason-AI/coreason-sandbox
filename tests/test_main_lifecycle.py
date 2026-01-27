from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_lifespan_calls_shutdown() -> None:
    # Patch the global sandbox in src.coreason_sandbox.main
    with patch("coreason_sandbox.main.sandbox") as mock_sandbox:
        mock_sandbox.shutdown = AsyncMock()

        # Import lifespan from main
        from coreason_sandbox.main import lifespan

        # Mock server object
        mock_server = MagicMock()

        # Use lifespan
        async with lifespan(mock_server):
            # Inside the context, shutdown should not be called yet
            mock_sandbox.shutdown.assert_not_called()

        # After exit, shutdown should be called
        mock_sandbox.shutdown.assert_called_once()
