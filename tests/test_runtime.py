# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from pathlib import Path
from typing import Literal, Any

import pytest
from coreason_identity.models import UserContext
from coreason_sandbox.models import ExecutionResult, FileReference
from coreason_sandbox.runtime import SandboxRuntime


class MockRuntime(SandboxRuntime):
    def __init__(self) -> None:
        self.is_running = False
        self.files: set[str] = set()

    async def start(self) -> None:
        self.is_running = True

    async def execute(
        self,
        code: str,
        language: Literal["python", "bash", "r"],
        context: UserContext,
        session_id: str,
    ) -> ExecutionResult:
        if not self.is_running:
            raise RuntimeError("Runtime not started")

        # Simulate artifact generation
        artifacts = []
        if "plot" in code:
            artifacts.append(FileReference(filename="plot.png", path="/tmp/plot.png"))
            self.files.add("/tmp/plot.png")

        return ExecutionResult(
            stdout="executed",
            stderr="",
            exit_code=0,
            artifacts=artifacts,
            execution_duration=0.5,
        )

    async def upload(self, local_path: Path, remote_path: str, context: UserContext, session_id: str) -> None:
        if not self.is_running:
            raise RuntimeError("Runtime not started")
        self.files.add(remote_path)

    async def download(self, remote_path: str, local_path: Path, context: UserContext, session_id: str) -> None:
        if not self.is_running:
            raise RuntimeError("Runtime not started")
        if remote_path not in self.files:
            raise FileNotFoundError(f"File {remote_path} not found")

    async def install_package(self, package_name: str, context: UserContext, session_id: str) -> None:
        if not self.is_running:
            raise RuntimeError("Runtime not started")

    async def list_files(self, path: str, context: UserContext, session_id: str) -> list[str]:
        if not self.is_running:
            raise RuntimeError("Runtime not started")
        return list(self.files)

    async def terminate(self) -> None:
        self.is_running = False
        self.files.clear()


class IncompleteRuntime(SandboxRuntime):
    # Missing abstract methods to test enforcement
    pass


@pytest.mark.asyncio
async def test_runtime_instantiation(mock_user_context: Any) -> None:
    runtime = MockRuntime()
    assert isinstance(runtime, SandboxRuntime)
    await runtime.start()
    result = await runtime.execute("print('hi')", "python", mock_user_context, "sid")
    assert result.stdout == "executed"
    await runtime.upload(Path("local"), "remote", mock_user_context, "sid")
    # Simulate file existing for download
    runtime.files.add("remote")
    await runtime.download("remote", Path("local"), mock_user_context, "sid")
    await runtime.terminate()


@pytest.mark.asyncio
async def test_complex_workflow(mock_user_context: Any) -> None:
    """
    Simulate a full lifecycle:
    1. Start
    2. Upload data
    3. Execute analysis (generates artifact)
    4. Download artifact
    5. Terminate
    """
    runtime = MockRuntime()

    # 1. Start
    await runtime.start()
    assert runtime.is_running

    # 2. Upload
    await runtime.upload(Path("data.csv"), "/home/user/data.csv", mock_user_context, "sid")
    assert "/home/user/data.csv" in runtime.files

    # 3. Execute
    result = await runtime.execute("import pandas; df.plot()", "python", mock_user_context, "sid")
    assert result.exit_code == 0
    assert len(result.artifacts) == 1
    assert result.artifacts[0].filename == "plot.png"
    assert "/tmp/plot.png" in runtime.files

    # 4. Download
    # Should succeed as file exists in mock state
    await runtime.download("/tmp/plot.png", Path("local_plot.png"), mock_user_context, "sid")

    # 5. Terminate
    await runtime.terminate()
    assert not runtime.is_running
    assert len(runtime.files) == 0


@pytest.mark.asyncio
async def test_runtime_state_enforcement(mock_user_context: Any) -> None:
    """Ensure operations fail if runtime is not started."""
    runtime = MockRuntime()

    with pytest.raises(RuntimeError, match="Runtime not started"):
        await runtime.execute("print('fail')", "python", mock_user_context, "sid")

    with pytest.raises(RuntimeError, match="Runtime not started"):
        await runtime.upload(Path("x"), "y", mock_user_context, "sid")


def test_abstract_method_enforcement() -> None:
    with pytest.raises(TypeError):
        IncompleteRuntime()  # type: ignore
