import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from coreason_sandbox.mcp import SandboxMCP

@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    runtime.terminate = AsyncMock()
    return runtime

@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.mcp.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock

@pytest.mark.asyncio
async def test_reaper_cancellation_coverage(mock_factory: Any, mock_runtime: Any) -> None:
    """
    Explicitly test that the reaper loop catches asyncio.CancelledError.
    This covers lines 60-61 in mcp.py.
    """
    mcp = SandboxMCP()

    # Start the reaper
    await mcp._start_reaper_if_needed()
    assert mcp._reaper_task is not None

    # Give it a moment to enter the loop and sleep
    await asyncio.sleep(0.01)

    # Cancel it manually
    mcp._reaper_task.cancel()

    # Await it - it should NOT raise CancelledError because it catches it
    await mcp._reaper_task

    # Verify it is done
    assert mcp._reaper_task.done()
