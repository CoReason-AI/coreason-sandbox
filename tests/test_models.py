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
from pydantic import ValidationError

from coreason_sandbox.models import ExecutionResult, FileReference


def test_file_reference_creation() -> None:
    ref = FileReference(filename="test.png", path="/tmp/test.png", content_type="image/png")
    assert ref.filename == "test.png"
    assert ref.path == "/tmp/test.png"
    assert ref.content_type == "image/png"
    assert ref.size_bytes is None
    assert ref.url is None


def test_execution_result_creation() -> None:
    artifacts = [
        FileReference(filename="plot.png", path="/home/user/plot.png"),
        FileReference(filename="data.csv", path="/home/user/data.csv"),
    ]
    result = ExecutionResult(
        stdout="hello",
        stderr="",
        exit_code=0,
        artifacts=artifacts,
        execution_duration=1.23,
    )
    assert result.stdout == "hello"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert len(result.artifacts) == 2
    assert result.execution_duration == 1.23
    assert result.artifacts[0].filename == "plot.png"


def test_model_validation_failures() -> None:
    # Test missing required field in FileReference
    with pytest.raises(ValidationError) as excinfo:
        FileReference(filename="test.png")  # type: ignore # Missing path
    assert "path" in str(excinfo.value)

    # Test missing required field in ExecutionResult
    with pytest.raises(ValidationError) as excinfo:
        ExecutionResult(
            stdout="out",
            stderr="err",
            exit_code=0,
            # Missing artifacts and execution_duration
        )  # type: ignore
    assert "artifacts" in str(excinfo.value)
    assert "execution_duration" in str(excinfo.value)

    # Test invalid type
    with pytest.raises(ValidationError) as excinfo:
        ExecutionResult(
            stdout="out",
            stderr="err",
            exit_code="not-an-int",  # type: ignore
            artifacts=[],
            execution_duration=1.0,
        )
    assert "exit_code" in str(excinfo.value)


def test_edge_case_values() -> None:
    # Negative exit code (e.g., terminated by signal)
    result = ExecutionResult(stdout="", stderr="Killed", exit_code=-9, artifacts=[], execution_duration=0.5)
    assert result.exit_code == -9

    # Empty strings
    ref = FileReference(filename="", path="")
    assert ref.filename == ""
    assert ref.path == ""

    # Large payload
    large_stdout = "a" * 1_000_000
    result_large = ExecutionResult(
        stdout=large_stdout,
        stderr="",
        exit_code=0,
        artifacts=[],
        execution_duration=10.5,
    )
    assert len(result_large.stdout) == 1_000_000


def test_execution_result_serialization() -> None:
    ref = FileReference(filename="test.txt", path="/tmp/test.txt")
    result = ExecutionResult(
        stdout="ok",
        stderr="",
        exit_code=0,
        artifacts=[ref],
        execution_duration=0.1,
    )

    # Verify dumping to dict
    data = result.model_dump()
    assert data["stdout"] == "ok"
    assert data["artifacts"][0]["filename"] == "test.txt"

    # Verify dumping to JSON
    json_str = result.model_dump_json()
    assert '"stdout":"ok"' in json_str
    assert '"filename":"test.txt"' in json_str
