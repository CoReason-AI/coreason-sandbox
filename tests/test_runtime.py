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
from typing import Literal

import pytest
from coreason_sandbox.models import ExecutionResult
from coreason_sandbox.runtime import SandboxRuntime


class MockRuntime(SandboxRuntime):
    async def start(self) -> None:
        pass

    async def execute(self, code: str, language: Literal["python", "bash", "r"]) -> ExecutionResult:
        return ExecutionResult(
            stdout="mock",
            stderr="",
            exit_code=0,
            artifacts=[],
            execution_duration=0.1,
        )

    async def upload(self, local_path: Path, remote_path: str) -> None:
        pass

    async def download(self, remote_path: str, local_path: Path) -> None:
        pass

    async def terminate(self) -> None:
        pass


class IncompleteRuntime(SandboxRuntime):
    # Missing abstract methods to test enforcement
    pass


@pytest.mark.asyncio
async def test_runtime_instantiation() -> None:
    runtime = MockRuntime()
    assert isinstance(runtime, SandboxRuntime)
    await runtime.start()
    result = await runtime.execute("print('hi')", "python")
    assert result.stdout == "mock"
    await runtime.upload(Path("local"), "remote")
    await runtime.download("remote", Path("local"))
    await runtime.terminate()


def test_abstract_method_enforcement() -> None:
    with pytest.raises(TypeError):
        IncompleteRuntime()  # type: ignore
