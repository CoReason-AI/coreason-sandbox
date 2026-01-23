from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxConfig(BaseSettings):
    """
    Configuration for the Sandbox environment.
    """

    runtime: Literal["docker", "e2b"] = "docker"

    model_config = SettingsConfigDict(
        env_prefix="COREASON_SANDBOX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
