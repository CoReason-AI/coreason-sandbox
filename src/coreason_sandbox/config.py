# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

"""Pydantic models for sandbox configuration."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxConfig(BaseSettings):
    """Configuration for the sandbox runtime environment."""

    model_config = SettingsConfigDict(env_prefix="SANDBOX_")

    RUNTIME: Literal["docker", "e2b"] = "docker"
    E2B_API_KEY: str | None = None
