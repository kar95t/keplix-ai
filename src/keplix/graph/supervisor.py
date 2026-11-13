"""Dynamic Planner Supervisor using LangGraph Command(goto=...) and Send() fan-out."""

from typing import Any, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command, Send

from keplix.graph.hitl import interrupt_for_approval
from keplix.graph.state import KeplixState, PlanContract, TaskContract, TaskStatus
from keplix.llm.factory import ModelRouter
from keplix.llm.structured import with_structured_retry

SUPERVISOR_SYSTEM_PROMPT = """You are the Keplix Dynamic Supervisor.
Your role is to decompose high-level engineering goals into isolated, typed task contracts.
Follow these rigid orbital rules:
1. Ensure parallel tasks do NOT overlap in target_files (prevent subgraph write conflicts).
2. Assign appropriate capability tiers ('coder' for heavy logic, 'fast' for lints/tests).
3. Whitelist strictly necessary tools for each task.
"""


def supervisor_node(state: KeplixState) -> Union[Command[Any], dict[str, Any]]:
    """Supervisor decision node: drafts plan, monitors worker outputs, and fans out subtasks."""
    goal = state.get("goal", "")
    plan = state.get("plan")
    tasks = state.get("tasks", [])
    worker_outputs = state.get("worker_outputs", [])

    # Step 1: Draft initial plan if not yet created
    if not plan:
        router = ModelRouter()
        architect_model = router.architect

        prompt = f"Engineering Goal: {goal}\nDraft a robust, decomposed execution plan."
        messages = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        generated_plan: PlanContract = with_structured_retry(
            model=architect_model,
            schema=PlanContract,
            messages=messages,
        )

        # Trigger Human-in-the-Loop approval for plan before fanout
        approved_plan = interrupt_for_approval(generated_plan)

        return Command(
            goto="supervisor",
            update={
                "plan": approved_plan,
                "tasks": approved_plan.tasks,
                "iteration": 1,
            },
        )

    # Step 2: Reconcile completed worker outputs into task state
    output_map = {out.task_id: out for out in worker_outputs}
    all_done = True
    executable_tasks: list[TaskContract] = []

    for task in tasks:
        if task.task_id in output_map:
            out = output_map[task.task_id]
            task.status = out.status

        if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
            all_done = False
            executable_tasks.append(task)
        elif task.status == TaskStatus.FAILED and task.retry_count < 3:
            all_done = False
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            executable_tasks.append(task)

    # Step 3: Check completion
    if all_done:
        return Command(
            goto=END,
            update={"is_complete": True},
        )

    # Step 4: Fan out parallel worker nodes via Send()
    fanout_sends = [
        Send("worker", {"task": task, "goal": goal})
        for task in executable_tasks
    ]

    if not fanout_sends:
        return Command(goto=END, update={"is_complete": True})

    return Command(goto=fanout_sends)


def plan_and_fanout(state: KeplixState) -> Union[Command[Any], dict[str, Any]]:
    """Convenience alias for supervisor orchestration step."""
    return supervisor_node(state)

