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


def test_sandbox_sync_execute(mock_runtime: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        with Sandbox() as svc:
            result = svc.execute("print('hello')")
            assert isinstance(result, ExecutionResult)
            assert result.stdout == "out"
            mock_runtime.execute.assert_awaited_once_with("print('hello')", "python")


def test_sandbox_sync_methods(mock_runtime: Any, tmp_path: Any) -> None:
    with patch("coreason_sandbox.sandbox.SandboxFactory.get_runtime", return_value=mock_runtime):
        with Sandbox() as svc:
            svc.install_package("requests")
            mock_runtime.install_package.assert_awaited_once_with("requests")

            files = svc.list_files()
            assert files == ["file1", "file2"]
            mock_runtime.list_files.assert_awaited_once_with(".")

            local_path = tmp_path / "test.txt"
            svc.upload(local_path, "remote.txt")
            mock_runtime.upload.assert_awaited_once_with(local_path, "remote.txt")

            svc.download("remote.txt", local_path)
            mock_runtime.download.assert_awaited_once_with("remote.txt", local_path)
