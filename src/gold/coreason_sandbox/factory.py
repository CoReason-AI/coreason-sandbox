from silver.interfaces import SandboxRuntime
def get_runtime() -> SandboxRuntime:
    from .runtimes.docker import DockerRuntime
    return DockerRuntime()
