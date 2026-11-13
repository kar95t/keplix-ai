"""LangGraph TypedDict state and Pydantic v2 hand-off contracts."""

from enum import Enum
import operator
from typing import Annotated, Any, Optional, TypedDict

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Execution status of an individual orchestrated task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskContract(BaseModel):
    """Typed Pydantic contract defining an isolated task handed off to a worker."""

    task_id: str = Field(description="Unique task identifier, e.g. 'task_ast_01'")
    role: str = Field(description="Target worker archetype, e.g. 'coder', 'tester', 'reviewer'")
    tier: str = Field(default="coder", description="Capability model tier ('architect', 'coder', 'fast')")
    description: str = Field(description="Specific, actionable task requirements")
    target_files: list[str] = Field(default_factory=list, description="Files requiring exclusive write-locks")
    required_tools: list[str] = Field(default_factory=list, description="Whitelisted tools for this agent's scope")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    retry_count: int = Field(default=0)


class PlanContract(BaseModel):
    """Global execution plan drafted by the Dynamic Supervisor."""

    goal: str = Field(description="User specified high-level objective")
    tasks: list[TaskContract] = Field(description="List of decomposed, dependency-ordered tasks")
    rationale: str = Field(description="Architectural rationale for this task decomposition")
    estimated_blast_radius: list[str] = Field(default_factory=list)


class WorkerOutputContract(BaseModel):
    """Typed result returned by a worker upon task execution."""

    task_id: str
    agent_id: str
    status: TaskStatus
    summary: str
    modified_files: list[str] = Field(default_factory=list)
    tests_passed: bool = True
    error_message: Optional[str] = None
    cost_usd: float = 0.0


class KeplixState(TypedDict, total=False):
    """Shared state graph blackboard for LangGraph multi-agent orchestration."""

    goal: str
    plan: Optional[PlanContract]
    tasks: list[TaskContract]
    worker_outputs: Annotated[list[WorkerOutputContract], operator.add]
    active_locks: dict[str, str]  # file_path -> agent_id
    budget_spent_usd: float
    iteration: int
    is_complete: bool
    error: Optional[str]
    metadata: dict[str, Any]

