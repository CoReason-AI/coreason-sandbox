from coreason_sandbox.artifacts import ArtifactManager
from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.runtime import SandboxRuntime
from coreason_sandbox.runtimes.docker import DockerRuntime
from coreason_sandbox.runtimes.e2b import E2BRuntime
from coreason_sandbox.storage import S3Storage


class SandboxFactory:
    """
    Factory to create SandboxRuntime instances based on configuration.
    """

    @staticmethod
    def get_runtime(config: SandboxConfig) -> SandboxRuntime:
        """
        Returns an instance of the configured SandboxRuntime.
        """
        # Initialize storage backend if configured
        storage = None
        if config.s3_bucket:
            storage = S3Storage(
                bucket=config.s3_bucket,
                region=config.s3_region,
                access_key=config.s3_access_key,
                secret_key=config.s3_secret_key,
                endpoint_url=config.s3_endpoint_url,
            )

        artifact_manager = ArtifactManager(storage=storage)

        if config.runtime == "docker":
            return DockerRuntime(
                image=config.docker_image,
                allowed_packages=config.allowed_packages,
                timeout=config.execution_timeout,
                artifact_manager=artifact_manager,
            )
        elif config.runtime == "e2b":
            return E2BRuntime(
                api_key=config.e2b_api_key,
                timeout=config.execution_timeout,
                artifact_manager=artifact_manager,
            )
        else:
            # This should be unreachable due to Pydantic validation, but for safety:
            raise ValueError(f"Unknown runtime: {config.runtime}")  # pragma: no cover
