# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from typing import Any, Literal, cast

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from coreason_sandbox.mcp import SandboxMCP

# Initialize Sandbox Logic
sandbox = SandboxMCP()

# Initialize MCP Server
mcp = FastMCP("coreason-sandbox")


@mcp.tool()  # type: ignore[misc]
async def execute_code(
    session_id: str, language: Literal["python", "bash", "r"], code: str
) -> list[TextContent | ImageContent]:
    """
    Execute code in the sandbox.
    Returns stdout, stderr, and any generated image artifacts.
    """
    try:
        # execute_code returns a dict with stdout, stderr, exit_code, artifacts
        result = await sandbox.execute_code(session_id, language, code)
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing code: {e!s}")]

    output: list[TextContent | ImageContent] = []

    # Safe casting for mypy, as we know the structure from SandboxMCP
    stdout = cast(str, result.get("stdout", ""))
    stderr = cast(str, result.get("stderr", ""))
    exit_code = cast(int, result.get("exit_code", 0))
    execution_duration = cast(float, result.get("execution_duration", 0.0))
    artifacts = cast(list[dict[str, Any]], result.get("artifacts", []))

    # Stdout
    if stdout:
        output.append(TextContent(type="text", text=f"STDOUT:\n{stdout}"))

    # Stderr
    if stderr:
        output.append(TextContent(type="text", text=f"STDERR:\n{stderr}"))

    # Exit Code
    output.append(TextContent(type="text", text=f"Exit Code: {exit_code}"))

    # Duration
    if execution_duration:
        output.append(TextContent(type="text", text=f"Duration: {execution_duration:.4f}s"))

    # Artifacts
    for artifact in artifacts:
        url = cast(str | None, artifact.get("url"))
        filename = cast(str, artifact.get("filename", "unknown"))
        content_type = cast(str, artifact.get("content_type", "application/octet-stream"))

        if url and url.startswith("data:image/"):
            # Parse data URL: data:image/png;base64,....
            try:
                header, base64_data = url.split(",", 1)
                # header e.g. "data:image/png;base64"
                # content_type from artifact or parsed from header

                # Use content_type from artifact if valid, else parse header
                if "image" not in content_type:
                    mime = header.split(":")[1].split(";")[0]
                else:
                    mime = content_type

                output.append(ImageContent(type="image", data=base64_data, mimeType=mime))
            except Exception as e:
                output.append(
                    TextContent(
                        type="text",
                        text=f"Failed to process image artifact {filename}: {e!s}",
                    )
                )
        else:
            output.append(
                TextContent(
                    type="text",
                    text=f"Artifact: {filename} ({url if url else 'No URL'})",
                )
            )

    return output


@mcp.tool()  # type: ignore[misc]
async def install_package(session_id: str, package_name: str) -> str:
    """
    Install a package in the sandbox session.
    """
    try:
        return await sandbox.install_package(session_id, package_name)
    except Exception as e:
        return f"Error installing package: {e!s}"


@mcp.tool()  # type: ignore[misc]
async def list_files(session_id: str, path: str = ".") -> list[str]:
    """
    List files in the sandbox session directory.
    """
    try:
        return await sandbox.list_files(session_id, path)
    except Exception as e:
        return [f"Error listing files: {e!s}"]


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
