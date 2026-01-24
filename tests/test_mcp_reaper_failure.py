from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from coreason_sandbox.mcp import SandboxMCP


@pytest.fixture
def mock_runtime() -> Any:
    runtime = AsyncMock()
    runtime.start = AsyncMock()
    return runtime


@pytest.fixture
def mock_factory(mock_runtime: Any) -> Any:
    with patch("coreason_sandbox.mcp.SandboxFactory.get_runtime", return_value=mock_runtime) as mock:
        yield mock


@pytest.mark.asyncio
async def test_reaper_exception_handling(mock_factory: Any, mock_runtime: Any) -> None:
    mcp = SandboxMCP()

    # Patch sleep to raise Exception immediately
    # We patch it in the module coreason_sandbox.mcp
    with patch("coreason_sandbox.mcp.asyncio.sleep", side_effect=Exception("Crash")):
        await mcp._start_reaper_if_needed()

        assert mcp._reaper_task is not None

        # The task should complete (crash caught and handled)
        await mcp._reaper_task

        assert mcp._reaper_task.done()
        # Exception should not propagate out of the task await
