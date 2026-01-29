from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.sandbox import Sandbox


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


def test_sandbox_sync_lifecycle(mock_runtime: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        # We use 'with' (sync context manager) which internally uses anyio.run
        with Sandbox() as _:
            pass

        # Verify async methods were called (via anyio.run)
        mock_runtime.start.assert_awaited_once()
        mock_runtime.terminate.assert_awaited_once()


def test_sandbox_sync_execute(mock_runtime: Any, mock_user_context: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        with Sandbox() as svc:
            result = svc.execute("print('hello')", mock_user_context)
            assert isinstance(result, ExecutionResult)
            assert result.stdout == "out"
            # execute uses a dynamic session ID, so we check using any() or just that it was called
            mock_runtime.execute.assert_awaited_once()
            args, _ = mock_runtime.execute.call_args
            assert args[0] == "print('hello')"
            assert args[1] == "python"
            assert args[2] == mock_user_context


def test_sandbox_sync_methods(mock_runtime: Any, tmp_path: Any, mock_user_context: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        with Sandbox() as svc:
            svc.install_package("requests", mock_user_context)
            mock_runtime.install_package.assert_awaited_once()

            files = svc.list_files(mock_user_context)
            assert files == ["file1", "file2"]
            mock_runtime.list_files.assert_awaited_once()

            local_path = tmp_path / "test.txt"
            svc.upload(local_path, "remote.txt", mock_user_context)
            mock_runtime.upload.assert_awaited_once()

            svc.download("remote.txt", local_path, mock_user_context)
            mock_runtime.download.assert_awaited_once()
