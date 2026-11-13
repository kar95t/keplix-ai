"""Integration tests for LangGraph state machine flow and worker execution."""

from keplix.graph.state import KeplixState, PlanContract, TaskContract, TaskStatus
from keplix.graph.supervisor import supervisor_node
from keplix.graph.worker import universal_worker_node


def test_supervisor_reconciliation_flow() -> None:
    task = TaskContract(
        task_id="t_101",
        role="fast",
        tier="fast",
        description="Verify linting",
    )
    plan = PlanContract(
        goal="Lint the repository",
        tasks=[task],
        rationale="Single check task",
    )

    state: KeplixState = {
        "goal": "Lint the repository",
        "plan": plan,
        "tasks": [task],
        "worker_outputs": [],
    }

    cmd = supervisor_node(state)
    assert cmd is not None

