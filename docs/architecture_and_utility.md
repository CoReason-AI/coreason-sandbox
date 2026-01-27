# The Architecture and Utility of coreason-sandbox

## 1. The Philosophy (The Why)

In the emerging ecosystem of autonomous agents, a critical dichotomy exists between the "Brain" and the "Hands." Large Language Models (LLMs) serve as excellent semantic engines—reasoning, planning, and understanding intent—but they are notoriously unreliable computation engines. When an agent attempts to perform statistical analysis or complex arithmetic purely through token prediction, it hallucinates. Conversely, allowing an agent to execute generated code directly on a host machine introduces catastrophic Remote Code Execution (RCE) vulnerabilities.

**coreason-sandbox** resolves this tension by providing a secure, ephemeral execution environment. It acts as the deterministic "Hands" for the agent's "Brain."

The architectural intent is strictly **runtime agnostic**. The consuming agent should not care whether its code is executing in a local Docker container or a microVM in the cloud; it only cares that the execution is isolated, the results are accurate, and the artifacts (like charts or CSVs) are retrievable. This package transforms code execution from a security liability into a reliable, observable utility, ensuring that when an agent needs to calculate, it calculates—it doesn't guess.

## 2. Under the Hood (The Dependencies & logic)

The package is built on a robust, modular stack designed for stability and flexibility.

*   **`mcp` (Model Context Protocol):** This is the primary interface layer. By adhering to the MCP standard, `coreason-sandbox` becomes plug-and-play for any MCP-compliant agent client, exposing tools like `execute_code` and `install_package` without requiring custom integration logic.
*   **`docker` & `e2b-code-interpreter`:** These dependencies represent the concrete implementations of the **Strategy Pattern** at the heart of the system.
    *   The `docker` library drives the `DockerRuntime`, enabling local, air-gapped, or on-premise deployments where data sovereignty is paramount.
    *   The `e2b-code-interpreter` powers the `E2BRuntime`, facilitating scalable, cloud-native execution with rapid boot times for production SaaS environments.
*   **`pydantic` & `pydantic-settings`:** Configuration management is strict and type-safe. The `SandboxConfig` handles the complexity of switching between runtimes (e.g., toggling between local sockets and cloud API keys) via environment variables, ensuring the application fails fast on misconfiguration.
*   **`loguru`:** Observability is baked in, providing structured logging for every execution lifecycle event—critical for forensic auditing of agent behavior.

Internally, the logic revolves around the `SessionManager`. Rather than spinning up a new environment for every single line of code (which is slow), the manager maintains "warm" sessions. It handles the delicate lifecycle of booting a sandbox, holding it open for iterative tasks (statefulness), and employing a "reaper" background task to ruthlessly terminate idle sessions, preventing resource leaks.

## 3. In Practice (The How)

The following examples demonstrate how `coreason-sandbox` abstracts the complexity of infrastructure management, allowing developers to focus on execution logic.

### Direct Programmatic Usage

For deep integration, you can interact directly with the `SessionManager`. This snippet demonstrates the "Happy Path" of initializing a session, running a calculation, and ensuring clean termination. Notice how the specific runtime (Docker vs. E2B) is abstracted away by the configuration.

```python
import asyncio
from coreason_sandbox.session_manager import SessionManager

async def run_calculation():
    # Initialize the manager; it automatically selects the runtime
    # based on your environment configuration.
    manager = SessionManager()

    # Acquire a session (boots a container or connects to a cloud VM)
    session = await manager.get_or_create_session("analysis-task-001")

    # The agent submits code to be executed securely
    code = """
import math
result = math.factorial(10)
print(f"The factorial of 10 is {result}")
    """

    # Execute and capture the result
    execution = await session.runtime.execute(code, language="python")

    print(f"Output: {execution.stdout.strip()}")
    # Output: The factorial of 10 is 3628800

    # Clean up resources
    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(run_calculation())
```

### The MCP Server Entry Point

In a production agent deployment, `coreason-sandbox` typically runs as a standalone server process. The `SandboxMCP` class wraps the logic, exposing it as standard tooling. The internal `lifespan` manager ensures that even when running as a server, background tasks like the session reaper are properly managed.

```python
# src/coreason_sandbox/main.py (Simplified View)

from mcp.server.fastmcp import FastMCP
from coreason_sandbox.mcp import SandboxMCP

# Initialize the logic core
sandbox = SandboxMCP()

# Define the server with lifecycle management
mcp = FastMCP("coreason-sandbox")

@mcp.tool()
async def execute_code(session_id: str, language: str, code: str):
    """
    Exposed tool for Agents: Executes code and returns logs + artifacts.
    """
    return await sandbox.execute_code(session_id, language, code)

# When this server runs, it becomes a "tool provider" for any connected Agent.
```
