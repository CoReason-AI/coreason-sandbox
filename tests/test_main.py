# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

import base64
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import ImageContent, TextContent

from coreason_sandbox.main import execute_code, install_package, list_files, main


@pytest.fixture
def mock_sandbox() -> Generator[MagicMock, None, None]:
    with patch("coreason_sandbox.main.sandbox", new_callable=MagicMock) as mock:
        # Configure methods to be awaitable
        mock.execute_code = AsyncMock()
        mock.install_package = AsyncMock()
        mock.list_files = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_execute_code_text_only(mock_sandbox: MagicMock) -> None:
    # Setup
    mock_sandbox.execute_code.return_value = {
        "stdout": "hello",
        "stderr": "",
        "exit_code": 0,
        "execution_duration": 1.23456,
        "artifacts": [],
    }

    # Execute
    result = await execute_code("session-1", "python", "print('hello')")

    # Verify
    # Order: Stdout, Stderr (skipped if empty), Exit Code, Duration, Artifacts
    assert len(result) == 3
    assert isinstance(result[0], TextContent)
    assert result[0].text == "STDOUT:\nhello"
    assert result[1].text == "Exit Code: 0"
    assert result[2].text == "Duration: 1.2346s"


@pytest.mark.asyncio
async def test_execute_code_stderr(mock_sandbox: MagicMock) -> None:
    # Setup
    mock_sandbox.execute_code.return_value = {
        "stdout": "",
        "stderr": "oops",
        "exit_code": 1,
        "execution_duration": 0.1,
        "artifacts": [],
    }

    # Execute
    result = await execute_code("session-1", "python", "error")

    # Verify
    assert len(result) == 3
    assert result[0].text == "STDERR:\noops"
    assert result[1].text == "Exit Code: 1"


@pytest.mark.asyncio
async def test_execute_code_with_image(mock_sandbox: MagicMock) -> None:
    # Setup
    img_bytes = b"fake_image_data"
    b64_img = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:image/png;base64,{b64_img}"

    mock_sandbox.execute_code.return_value = {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "execution_duration": 0.5,
        "artifacts": [
            {
                "filename": "plot.png",
                "url": data_url,
                "content_type": "image/png",
            }
        ],
    }

    # Execute
    result = await execute_code("session-1", "python", "plot()")

    # Verify
    # Expect [Exit Code, Duration, Image]
    assert len(result) == 3
    assert result[0].text == "Exit Code: 0"
    assert result[1].text == "Duration: 0.5000s"

    img_result = result[2]
    assert isinstance(img_result, ImageContent)
    assert img_result.data == b64_img
    assert img_result.mimeType == "image/png"


@pytest.mark.asyncio
async def test_execute_code_with_image_missing_content_type(mock_sandbox: MagicMock) -> None:
    # Setup
    img_bytes = b"fake_image_data"
    b64_img = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:image/png;base64,{b64_img}"

    mock_sandbox.execute_code.return_value = {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "execution_duration": 0.5,
        "artifacts": [
            {
                "filename": "plot.png",
                "url": data_url,
                "content_type": "application/octet-stream",  # Not image/
            }
        ],
    }

    # Execute
    result = await execute_code("session-1", "python", "plot()")

    # Verify it inferred from data url header
    img_result = result[2]
    assert isinstance(img_result, ImageContent)
    assert img_result.mimeType == "image/png"


@pytest.mark.asyncio
async def test_execute_code_malformed_image_url(mock_sandbox: MagicMock) -> None:
    # Setup
    mock_sandbox.execute_code.return_value = {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "execution_duration": 0.5,
        "artifacts": [
            {
                "filename": "plot.png",
                "url": "data:image/png;base64_NO_COMMA",  # Malformed, no comma
                "content_type": "image/png",
            }
        ],
    }

    # Execute
    result = await execute_code("session-1", "python", "plot()")

    # Verify fallback to text error
    assert "Failed to process image artifact" in result[2].text


@pytest.mark.asyncio
async def test_execute_code_with_non_image_artifact(mock_sandbox: MagicMock) -> None:
    # Setup
    mock_sandbox.execute_code.return_value = {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "execution_duration": 0.1,
        "artifacts": [
            {
                "filename": "data.csv",
                "url": "https://s3.bucket/data.csv",
                "content_type": "text/csv",
            }
        ],
    }

    # Execute
    result = await execute_code("session-1", "python", "save()")

    # Verify
    assert len(result) == 3
    assert "Artifact: data.csv (https://s3.bucket/data.csv)" in result[2].text


@pytest.mark.asyncio
async def test_execute_code_exception(mock_sandbox: MagicMock) -> None:
    mock_sandbox.execute_code.side_effect = Exception("Boom")

    result = await execute_code("sess", "python", "code")

    assert len(result) == 1
    assert "Error executing code: Boom" in result[0].text


@pytest.mark.asyncio
async def test_install_package(mock_sandbox: MagicMock) -> None:
    mock_sandbox.install_package.return_value = "Success"
    result = await install_package("sess", "pandas")
    assert result == "Success"


@pytest.mark.asyncio
async def test_install_package_exception(mock_sandbox: MagicMock) -> None:
    mock_sandbox.install_package.side_effect = Exception("Fail")
    result = await install_package("sess", "pandas")
    assert "Error installing package: Fail" in result


@pytest.mark.asyncio
async def test_list_files(mock_sandbox: MagicMock) -> None:
    mock_sandbox.list_files.return_value = ["file1", "file2"]
    result = await list_files("sess", ".")
    assert result == ["file1", "file2"]


@pytest.mark.asyncio
async def test_list_files_exception(mock_sandbox: MagicMock) -> None:
    mock_sandbox.list_files.side_effect = Exception("Fail")
    result = await list_files("sess", ".")
    assert result == ["Error listing files: Fail"]


def test_main_execution() -> None:
    with patch("coreason_sandbox.main.mcp.run") as mock_run:
        main()
        mock_run.assert_called_once()
