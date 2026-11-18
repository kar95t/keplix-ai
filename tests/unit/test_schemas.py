"""Unit tests for Pydantic v2 task, plan, and output contracts."""

import unittest

try:
    from pydantic import ValidationError
    from keplix.graph.state import (
        PlanContract,
        TaskContract,
        TaskStatus,
        WorkerOutputContract,
    )
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class TestSchemas(unittest.TestCase):
    @unittest.skipUnless(HAS_DEPS, "Pydantic or graph state dependencies not installed")
    def test_task_contract_validation(self) -> None:
        task = TaskContract(
            task_id="t_001",
            role="coder",
            description="Implement fast matrix multiplication",
            target_files=["math/matrix.py"],
            required_tools=["read_workspace_file", "apply_diff_patch"],
        )
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.retry_count, 0)
        self.assertIn("math/matrix.py", task.target_files)

    @unittest.skipUnless(HAS_DEPS, "Pydantic or graph state dependencies not installed")
    def test_plan_contract_structure(self) -> None:
        task1 = TaskContract(task_id="t_1", role="architect", description="Design API")
        task2 = TaskContract(task_id="t_2", role="coder", description="Build endpoints")

        plan = PlanContract(
            goal="Create REST API",
            tasks=[task1, task2],
            rationale="Decompose design from implementation",
        )
        self.assertEqual(len(plan.tasks), 2)
        dumped = plan.model_dump()
        self.assertEqual(dumped["goal"], "Create REST API")

    @unittest.skipUnless(HAS_DEPS, "Pydantic or graph state dependencies not installed")
    def test_worker_output_contract(self) -> None:
        output = WorkerOutputContract(
            task_id="t_1",
            agent_id="worker_coder_01",
            status=TaskStatus.COMPLETED,
            summary="Refactored parser",
            modified_files=["parser.py"],
            tests_passed=True,
        )
        self.assertEqual(output.status, TaskStatus.COMPLETED)
        self.assertTrue(output.tests_passed)

