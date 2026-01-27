# coreason-sandbox

> A secure, ephemeral execution environment designed to give CoReason Agents the ability to write and run code safely.

[![License: Prosperity 3.0](https://img.shields.io/badge/license-Prosperity%203.0-blue)](LICENSE)
[![CI/Status](https://github.com/CoReason-AI/coreason_sandbox/actions/workflows/ci.yml/badge.svg)](https://github.com/CoReason-AI/coreason_sandbox/actions)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Documentation](https://img.shields.io/badge/docs-PRD-brightgreen)](docs/product_requirements.md)

**coreason-sandbox** serves as the "Hands" for the "Brains" of the CoReason system. It solves the problem of hallucinated math and missing visuals by providing a real, isolated Linux runtime where Python and R scripts can be executed deterministically. It abstracts the underlying compute engine, allowing seamless switching between local Docker containers (for development/on-prem) and cloud-based microVMs (E2B for production).

## Features

-   **Deterministic Execution**: Agents write Python code to calculate, ensuring 100% mathematical accuracy.
-   **Strict Isolation**: Code runs in disposable, network-isolated sandboxes that are destroyed immediately after use (preventing RCE).
-   **Artifact Capture**: Automatically captures filesystem changes (e.g., plot.png) and pipes them back to the user UI.
-   **Runtime Agnostic**: Switch seamlessly between local **Docker** containers and **E2B** Cloud microVMs using a Strategy Pattern.
-   **Lifecycle Management**: Automatic provisioning, keep-alive for iterative execution, and background reaping of idle sessions.
-   **Security**: Network isolation by default, strict package allowlisting (PyPI only), and resource throttling (CPU/Memory).

## Installation

```bash
pip install coreason-sandbox
```

## Usage

Here is a simple example of how to initialize and use the library to execute Python code:

```python
import asyncio
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.factory import SandboxFactory

async def main():
    # 1. Configure (defaults to Docker)
    config = SandboxConfig(
        runtime="docker",
        docker_image="python:3.12-slim"
    )

    # 2. Create Runtime
    runtime = SandboxFactory.get_runtime(config)

    # 3. Start & Execute
    await runtime.start()
    try:
        result = await runtime.execute("print(2 + 2)", language="python")
        print(f"Result: {result.stdout.strip()}")  # Output: Result: 4
    finally:
        await runtime.terminate()

if __name__ == "__main__":
    asyncio.run(main())
```
