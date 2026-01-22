# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

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
