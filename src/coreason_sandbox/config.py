from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxConfig(BaseSettings):  # type: ignore[misc]
    """Configuration for the Sandbox environment.

    Attributes:
        runtime: The runtime engine to use ('docker' or 'e2b'). Defaults to 'docker'.
        docker_image: The Docker image to use for the 'docker' runtime. Defaults to 'python:3.12-slim'.
        allowed_packages: A set of allowed Python packages for installation.
        execution_timeout: Maximum time (in seconds) allowed for a single code execution. Defaults to 60.0.
        idle_timeout: Maximum time (in seconds) a session can remain idle before being reaped. Defaults to 300.0.
        reaper_interval: Interval (in seconds) for the background session reaper to run. Defaults to 60.0.
        enable_audit_logging: Whether to enable Veritas audit logging. Defaults to True.
        e2b_api_key: API key for E2B runtime.
        s3_bucket: S3 bucket name for artifact storage.
        s3_region: S3 region name.
        s3_access_key: S3 access key ID.
        s3_secret_key: S3 secret access key.
        s3_endpoint_url: S3 endpoint URL (for MinIO or compatible services).
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
