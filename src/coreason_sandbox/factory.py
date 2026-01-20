# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""Factory for creating sandbox runtime instances."""

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.runtimes.base import SandboxRuntime
from coreason_sandbox.runtimes.docker import DockerRuntime
from coreason_sandbox.runtimes.e2b import E2BRuntime


def get_runtime(config: SandboxConfig | None = None) -> SandboxRuntime:
    """
    Create and return a sandbox runtime instance based on the configuration.

    Args:
        config: The sandbox configuration. If not provided, it will be loaded.

    Returns:
        An instance of a class that implements the SandboxRuntime interface.

    Raises:
        ValueError: If the E2B runtime is selected but no API key is provided.
    """
    if config is None:
        config = SandboxConfig()

    if config.RUNTIME == "docker":
        return DockerRuntime()
    elif config.RUNTIME == "e2b":
        if not config.E2B_API_KEY:
            raise ValueError("E2B_API_KEY must be set to use the E2B runtime.")
        return E2BRuntime()
    else:  # pragma: no cover
        # This case should be prevented by Pydantic's validation,
        # but it's good practice to handle it defensively.
        raise ValueError(f"Unknown RUNTIME '{config.RUNTIME}' specified in config.")
