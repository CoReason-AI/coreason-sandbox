from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.runtime import SandboxRuntime
from coreason_sandbox.runtimes.docker import DockerRuntime
from coreason_sandbox.runtimes.e2b import E2BRuntime


class SandboxFactory:
    """
    Factory to create SandboxRuntime instances based on configuration.
    """

    @staticmethod
    def get_runtime(config: SandboxConfig) -> SandboxRuntime:
        """
        Returns an instance of the configured SandboxRuntime.
        """
        if config.runtime == "docker":
            return DockerRuntime(allowed_packages=config.allowed_packages)
        elif config.runtime == "e2b":
            return E2BRuntime()
        else:
            # This should be unreachable due to Pydantic validation, but for safety:
            raise ValueError(f"Unknown runtime: {config.runtime}")  # pragma: no cover
