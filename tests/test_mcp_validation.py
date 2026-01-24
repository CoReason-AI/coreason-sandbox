import pytest
from coreason_sandbox.mcp import SandboxMCP

@pytest.mark.asyncio
async def test_mcp_validation_empty_session_id() -> None:
    mcp = SandboxMCP()

    with pytest.raises(ValueError, match="Session ID is required"):
        await mcp.execute_code("", "python", "print(1)")

    with pytest.raises(ValueError, match="Session ID is required"):
        await mcp.install_package("", "pandas")

    with pytest.raises(ValueError, match="Session ID is required"):
        await mcp.list_files("", ".")
