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
