"""Ephemeral Docker sandbox container lifecycle and execution runner."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None  # type: ignore[assignment]
    DockerException = Exception  # type: ignore[assignment,misc]


@dataclass
class ContainerExecutionResult:
    """Output result of executing a command inside an ephemeral container."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class DockerSandboxRunner:
    """Manages ephemeral container lifecycle with read-write workspace bind mounts."""

    def __init__(
        self,
        image: str = "python:3.12-slim",
        workspace_dir: Optional[Path] = None,
    ) -> None:
        self.image = image
        self.workspace_dir = (workspace_dir or Path.cwd()).resolve()
        self._client: Optional[docker.DockerClient] = None

    def _get_client(self) -> docker.DockerClient:
        """Lazily initialize and test the Docker engine client."""
        if docker is None:
            raise RuntimeError(
                "Docker Python SDK is not installed. Install with `uv pip install docker`."
            )
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except DockerException as e:
                raise RuntimeError(
                    f"Unable to connect to Docker daemon: {e}. Ensure Docker Desktop or dockerd is running."
                )
        return self._client

    def is_available(self) -> bool:
        """Check whether Docker daemon is reachable on this machine."""
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def run_command(
        self,
        cmd: str,
        timeout_seconds: int = 120,
        environment: Optional[dict[str, str]] = None,
    ) -> ContainerExecutionResult:
        """Execute a shell command inside an ephemeral container bind-mounted to the workspace."""
        client = self._get_client()

        mounts = {
            str(self.workspace_dir): {
                "bind": "/workspace",
                "mode": "rw",
            }
        }

        container = None
        try:
            container = client.containers.create(
                image=self.image,
                command=["sh", "-c", cmd],
                volumes=mounts,
                working_dir="/workspace",
                environment=environment or {},
                network_mode="bridge",
                mem_limit="2g",
                nano_cpus=2 * 1_000_000_000,
            )

            container.start()
            res = container.wait(timeout=timeout_seconds)
            exit_code = res.get("StatusCode", 1)

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            return ContainerExecutionResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
            )
        except Exception as exc:
            return ContainerExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Sandbox execution failed: {exc}",
                timed_out=True,
            )
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

