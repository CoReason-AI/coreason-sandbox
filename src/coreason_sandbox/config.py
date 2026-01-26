from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxConfig(BaseSettings):
    """
    Configuration for the Sandbox environment.
    """

    runtime: Literal["docker", "e2b"] = "docker"
    docker_image: str = "python:3.12-slim"

    allowed_packages: set[str] = {
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn",
        "scikit-learn",
        "scipy",
    }
    execution_timeout: float = 60.0
    idle_timeout: float = 300.0  # 5 minutes
    reaper_interval: float = 60.0  # Check every minute
    enable_audit_logging: bool = True

    # E2B Configuration
    e2b_api_key: str | None = None

    # S3 / Object Storage
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_endpoint_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="COREASON_SANDBOX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
