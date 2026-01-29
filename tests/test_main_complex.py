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

from coreason_sandbox.main import execute_code


@pytest.fixture
def mock_sandbox() -> Generator[MagicMock, None, None]:
    with patch("coreason_sandbox.main.sandbox", new_callable=MagicMock) as mock:
        mock.execute_code = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_execute_code_mixed_response(mock_sandbox: MagicMock) -> None:
    """
    Test a complex response with stdout, stderr, an image, and a file link.
    """
    img_bytes = b"image_data"
    b64_img = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64_img}"

    mock_sandbox.execute_code.return_value = {
        "stdout": "Standard Output",
        "stderr": "Standard Error",
        "exit_code": 0,
        "execution_duration": 1.5,
        "artifacts": [
            {
                "filename": "chart.jpg",
                "url": data_url,
                "content_type": "image/jpeg",
            },
            {
                "filename": "data.csv",
                "url": "https://s3.bucket/data.csv",
                "content_type": "text/csv",
            },
        ],
    }

    result = await execute_code("session-mixed", "python", "run_complex()")

    assert len(result) == 6  # Stdout, Stderr, Exit, Duration, Image, Link

    # Verify types and content
    assert isinstance(result[0], TextContent)
    assert "Standard Output" in result[0].text

    assert isinstance(result[1], TextContent)
    assert "Standard Error" in result[1].text

    assert isinstance(result[2], TextContent)
    assert "Exit Code: 0" in result[2].text

    assert isinstance(result[3], TextContent)
    assert "Duration: 1.5000s" in result[3].text

    # Image Artifact
    assert isinstance(result[4], ImageContent)
    assert result[4].mimeType == "image/jpeg"
    assert result[4].data == b64_img

    # File Link Artifact
    assert isinstance(result[5], TextContent)
    assert "Artifact: data.csv" in result[5].text
    assert "https://s3.bucket/data.csv" in result[5].text


@pytest.mark.asyncio
async def test_execute_code_artifact_edge_cases(mock_sandbox: MagicMock) -> None:
    """
    Test edge cases: missing fields, invalid base64, unknown structure.
    """
    mock_sandbox.execute_code.return_value = {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "execution_duration": 0.0,
        "artifacts": [
            # Case 1: Missing URL (Should fallback to text description)
            {
                "filename": "missing_url.txt",
                "content_type": "text/plain",
            },
            # Case 2: Invalid Base64 in Data URL (Should fallback to error text)
            {
                "filename": "corrupt.png",
                "url": "data:image/png;base64,!!!INVALID_BASE64!!!",
                "content_type": "image/png",
            },
            # Case 3: Missing filename (Should use default "unknown")
            {
                "url": "http://example.com/file",
                "content_type": "application/pdf",
            },
        ],
    }

    result = await execute_code("session-edge", "python", "run_edge()")

    # Expect: Exit Code + 3 Artifacts = 4 items (duration 0 is skipped)
    assert len(result) == 4

    # Case 1
    assert isinstance(result[1], TextContent)
    assert "Artifact: missing_url.txt (No URL)" in result[1].text

    # Case 2
    assert isinstance(result[2], TextContent)
    assert "Failed to process image artifact corrupt.png" in result[2].text

    # Case 3
    assert isinstance(result[3], TextContent)
    assert "Artifact: unknown" in result[3].text
    assert "http://example.com/file" in result[3].text


@pytest.mark.asyncio
async def test_execute_code_unicode(mock_sandbox: MagicMock) -> None:
    """
    Test preservation of Unicode characters.
    """
    unicode_str = "🚀 Hello World 🌍 - ¥€$"
    mock_sandbox.execute_code.return_value = {
        "stdout": unicode_str,
        "stderr": "",
        "exit_code": 0,
        "artifacts": [],
    }

    result = await execute_code("session-unicode", "python", "print('🚀')")

    assert isinstance(result[0], TextContent)
    assert f"STDOUT:\n{unicode_str}" == result[0].text
