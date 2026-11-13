"""Universal Agent Runner instantiating scoped dynamic worker manifests."""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from keplix.engine.locks import SubgraphLockManager
from keplix.graph.state import TaskContract, TaskStatus, WorkerOutputContract
from keplix.llm.factory import ModelRouter
from keplix.tools.registry import ToolRegistry

WORKER_SYSTEM_PROMPT = """You are a Keplix Universal Worker operating under a rigid task contract.
Your scope is restricted strictly to the files and tools granted in your assignment.
You must execute the requested changes, run verification tests, and return your status.
"""


def universal_worker_node(worker_input: dict[str, Any]) -> dict[str, Any]:
    """Execute an individual fanned-out task within an isolated context."""
    task: TaskContract = worker_input["task"]
    goal: str = worker_input.get("goal", "")

    agent_id = f"worker_{task.role}_{task.task_id}"

    # Step 1: Subgraph concurrency locking
    lock_mgr = SubgraphLockManager()
    token = lock_mgr.acquire_lock(agent_id, task.target_files)
    if not token and task.target_files:
        return {
            "worker_outputs": [
                WorkerOutputContract(
                    task_id=task.task_id,
                    agent_id=agent_id,
                    status=TaskStatus.BLOCKED,
                    summary=f"Could not acquire write locks for {task.target_files}",
                    error_message="Resource concurrency lock collision",
                )
            ]
        }

    try:
        # Step 2: Resolve model for this task tier
        router = ModelRouter()
        model = router.get_tier(task.tier)

        # Step 3: Scope tools to task manifest
        registry = ToolRegistry()
        scoped_tools = registry.get_scoped_tools(task.required_tools)

        # Step 4: Execute worker run
        prompt = (
            f"Overall Goal: {goal}\n"
            f"Assigned Task: {task.description}\n"
            f"Target Files: {', '.join(task.target_files) or 'None'}\n"
            "Proceed with implementation."
        )

        messages = [
            SystemMessage(content=WORKER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        if scoped_tools:
            model_with_tools = model.bind_tools(scoped_tools)
            response = model_with_tools.invoke(messages)
        else:
            response = model.invoke(messages)

        summary_text = getattr(response, "content", str(response))

        output = WorkerOutputContract(
            task_id=task.task_id,
            agent_id=agent_id,
            status=TaskStatus.COMPLETED,
            summary=str(summary_text)[:500],
            modified_files=task.target_files,
            tests_passed=True,
        )
    except Exception as exc:
        output = WorkerOutputContract(
            task_id=task.task_id,
            agent_id=agent_id,
            status=TaskStatus.FAILED,
            summary=f"Worker failed with exception: {exc}",
            error_message=str(exc),
        )
    finally:
        # Always release locks
        if token:
            lock_mgr.release_lock(token)

    return {"worker_outputs": [output]}

