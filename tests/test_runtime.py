# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

import pytest
from coreason_sandbox.runtime.base import SandboxRuntime
from coreason_sandbox.models.models import ExecutionResult

class ConcreteRuntime(SandboxRuntime):
    """A concrete implementation of SandboxRuntime for testing purposes."""
    async def start(self) -> None:
        pass

    async def execute(self, code: str, language: str) -> ExecutionResult:
        return ExecutionResult(stdout="", stderr="", exit_code=0, artifacts=[], execution_duration=0.0)

    async def upload(self, local_path, remote_path) -> None:
        pass

    async def download(self, remote_path, local_path) -> None:
        pass

    async def terminate(self) -> None:
        pass

def test_sandbox_runtime_instantiation():
    """Tests that a concrete implementation of SandboxRuntime can be instantiated."""
    try:
        runtime = ConcreteRuntime()
        assert isinstance(runtime, SandboxRuntime)
    except Exception as e:
        assert False, f"Failed to instantiate ConcreteRuntime: {e}"

def test_sandbox_runtime_abstract_methods():
    """Tests that SandboxRuntime enforces the implementation of abstract methods."""
    with pytest.raises(TypeError):
        class IncompleteRuntime(SandboxRuntime):
            pass
        IncompleteRuntime()
