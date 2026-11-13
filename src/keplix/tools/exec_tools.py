"""Container bash execution and test runner tools."""

import subprocess

from langchain_core.tools import tool

from keplix.engine.log_pruner import LogPruner
from keplix.sandbox.docker_runner import DockerSandboxRunner
from keplix.tools.registry import register_tool


@tool
def run_bash_command(cmd: str, timeout_seconds: int = 60) -> str:
    """Execute a bash shell command inside the isolated ephemeral Docker sandbox."""
    runner = DockerSandboxRunner()
    pruner = LogPruner()

    if runner.is_available():
        res = runner.run_command(cmd, timeout_seconds=timeout_seconds)
        output = f"Exit code: {res.exit_code}\nStdout:\n{res.stdout}\nStderr:\n{res.stderr}"
        return pruner.process(output)

    # Local fallback if Docker daemon is not active
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = f"Exit code: {proc.returncode}\nStdout:\n{proc.stdout}\nStderr:\n{proc.stderr}"
        return pruner.process(output)
    except subprocess.TimeoutExpired:
        return f"Command '{cmd}' timed out after {timeout_seconds} seconds."
    except Exception as e:
        return f"Failed to execute bash command: {e}"


@tool
def run_pytest_suite(test_path: str = "tests") -> str:
    """Run pytest suite on target tests and return compressed failure trace if any."""
    cmd = f"pytest {test_path} -v --tb=short"
    return run_bash_command.invoke({"cmd": cmd, "timeout_seconds": 90})


# Auto-register execution tools
register_tool(scope="exec")(run_bash_command)
register_tool(scope="exec")(run_pytest_suite)

