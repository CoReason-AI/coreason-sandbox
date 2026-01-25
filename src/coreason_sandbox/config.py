from typing import Any, Literal

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from coreason_sandbox.integrations.vault import VaultIntegrator


class VaultSettingsSource(PydanticBaseSettingsSource):
    """
    Custom Pydantic Settings Source that reads secrets from Vault.
    """

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        # This method is required by abstract base class, but since we implement __call__,
        # this is technically unused by Pydantic if __call__ returns the full dict.
        # However, to satisfy Mypy strict mode which sees the ABC method, we must return something.
        return None, field_name, False  # pragma: no cover

    def __call__(self) -> dict[str, Any]:
        vault = VaultIntegrator()
        secrets: dict[str, Any] = {}

        # Define mapping of Config Field -> Vault Key
        # This could be dynamic, but explicit is better for audit.
        mapping = {
            "e2b_api_key": "E2B_API_KEY",
            "s3_access_key": "S3_ACCESS_KEY",
            "s3_secret_key": "S3_SECRET_KEY",
        }

        for field, key in mapping.items():
            val = vault.get_secret(key)
            if val:
                secrets[field] = val

        return secrets


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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            VaultSettingsSource(settings_cls),
            file_secret_settings,
        )
