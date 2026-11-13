"""Unit tests for Pydantic v2 task, plan, and output contracts."""

import pytest
from pydantic import ValidationError

from keplix.graph.state import (
    PlanContract,
    TaskContract,
    TaskStatus,
    WorkerOutputContract,
)


def test_task_contract_validation() -> None:
    task = TaskContract(
        task_id="t_001",
        role="coder",
        description="Implement fast matrix multiplication",
        target_files=["math/matrix.py"],
        required_tools=["read_workspace_file", "apply_diff_patch"],
    )
    assert task.status == TaskStatus.PENDING
    assert task.retry_count == 0
    assert "math/matrix.py" in task.target_files


def test_plan_contract_structure() -> None:
    task1 = TaskContract(task_id="t_1", role="architect", description="Design API")
    task2 = TaskContract(task_id="t_2", role="coder", description="Build endpoints")

    plan = PlanContract(
        goal="Create REST API",
        tasks=[task1, task2],
        rationale="Decompose design from implementation",
    )
    assert len(plan.tasks) == 2
    dumped = plan.model_dump()
    assert dumped["goal"] == "Create REST API"


def test_worker_output_contract() -> None:
    output = WorkerOutputContract(
        task_id="t_1",
        agent_id="worker_coder_01",
        status=TaskStatus.COMPLETED,
        summary="Refactored parser",
        modified_files=["parser.py"],
        tests_passed=True,
    )
    assert output.status == TaskStatus.COMPLETED
    assert output.tests_passed is True

