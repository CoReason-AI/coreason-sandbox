from unittest.mock import patch

from coreason_sandbox.config import SandboxConfig
from coreason_sandbox.factory import SandboxFactory
from coreason_sandbox.runtime import SandboxRuntime
from coreason_sandbox.runtimes.docker import DockerRuntime
from coreason_sandbox.runtimes.e2b import E2BRuntime


def test_factory_returns_docker_runtime() -> None:
    config = SandboxConfig(runtime="docker")
    with patch("coreason_sandbox.runtimes.docker.docker.from_env"):
        runtime = SandboxFactory.get_runtime(config)
        assert isinstance(runtime, DockerRuntime)
        assert isinstance(runtime, SandboxRuntime)


def test_factory_returns_e2b_runtime() -> None:
    config = SandboxConfig(runtime="e2b")
    # E2B runtime might not need mocking if it only sets api_key in init,
    # but to be safe/clean if logic changes:
    runtime = SandboxFactory.get_runtime(config)
    assert isinstance(runtime, E2BRuntime)
    assert isinstance(runtime, SandboxRuntime)


def test_factory_wires_s3_storage() -> None:
    config = SandboxConfig(
        runtime="docker",
        s3_bucket="my-bucket",
        s3_region="us-east-1",
    )
    with (
        patch("coreason_sandbox.runtimes.docker.docker.from_env"),
        patch("coreason_sandbox.factory.S3Storage") as MockS3,
    ):
        runtime = SandboxFactory.get_runtime(config)

        # Check S3Storage initialized
        MockS3.assert_called_with(
            bucket="my-bucket",
            region="us-east-1",
            access_key=None,
            secret_key=None,
            endpoint_url=None,
        )

        # Check wired into runtime via artifact manager
        # Since artifact_manager is an instance, we can check its storage attribute if accessible
        # or assume if storage was created it was passed (given we tested the code logic)
        # But ArtifactManager.storage is public attribute
        assert hasattr(runtime, "artifact_manager")
        assert runtime.artifact_manager.storage == MockS3.return_value
