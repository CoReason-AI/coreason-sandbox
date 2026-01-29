from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.sandbox import SandboxAsync


@pytest.fixture
def mock_runtime() -> Any:
    mock = MagicMock()
    mock.start = AsyncMock()
    mock.terminate = AsyncMock()
    mock.execute = AsyncMock(
        return_value=ExecutionResult(stdout="out", stderr="", exit_code=0, execution_duration=0.1, artifacts=[])
    )
    mock.upload = AsyncMock()
    mock.download = AsyncMock()
    mock.install_package = AsyncMock()
    mock.list_files = AsyncMock(return_value=["file1", "file2"])
    return mock


@pytest.mark.asyncio
async def test_sandbox_async_lifecycle(mock_runtime: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        async with SandboxAsync() as svc:
            assert svc.runtime == mock_runtime

        mock_runtime.start.assert_awaited_once()
        mock_runtime.terminate.assert_awaited_once()


@pytest.mark.asyncio
async def test_sandbox_async_execute(mock_runtime: Any, mock_user_context: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        async with SandboxAsync() as svc:
            result = await svc.execute("print('hello')", mock_user_context)
            assert isinstance(result, ExecutionResult)
            assert result.stdout == "out"
            mock_runtime.execute.assert_awaited_once_with("print('hello')", "python", mock_user_context, svc.session_id)


@pytest.mark.asyncio
async def test_sandbox_async_methods(mock_runtime: Any, tmp_path: Any, mock_user_context: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        async with SandboxAsync() as svc:
            await svc.install_package("requests", mock_user_context)
            mock_runtime.install_package.assert_awaited_once_with("requests", mock_user_context, svc.session_id)

            await svc.list_files(mock_user_context)
            mock_runtime.list_files.assert_awaited_once_with(".", mock_user_context, svc.session_id)

            local_path = tmp_path / "test.txt"
            await svc.upload(local_path, "remote.txt", mock_user_context)
            mock_runtime.upload.assert_awaited_once_with(local_path, "remote.txt", mock_user_context, svc.session_id)

            await svc.download("remote.txt", local_path, mock_user_context)
            mock_runtime.download.assert_awaited_once_with("remote.txt", local_path, mock_user_context, svc.session_id)
