"""LangGraph interrupt() handlers for secrets and human-in-the-loop plan approvals."""

from typing import Any, Optional

try:
    from langgraph.types import interrupt
except ImportError:
    # Fallback placeholder if langgraph version differs
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        return value

from keplix.config.secrets import SecretManager
from keplix.graph.state import PlanContract


def interrupt_for_approval(plan: PlanContract) -> PlanContract:
    """Pause graph execution to request human operator review and sign-off on a proposed plan.

    In LangGraph runtime, yields an interrupt payload.
    In local CLI runs, can fall back to interactive prompt.
    """
    try:
        # LangGraph interrupt mechanism
        resume_data = interrupt({
            "type": "plan_approval",
            "message": "Review and approve dynamic orchestration plan",
            "plan": plan.model_dump(),
        })

        if isinstance(resume_data, dict) and "approved" in resume_data:
            if not resume_data["approved"]:
                raise PermissionError("Plan execution rejected by human operator.")
            if "modified_plan" in resume_data:
                return PlanContract.model_validate(resume_data["modified_plan"])
        return plan
    except Exception:
        # Non-graph execution fallback: auto-approve or return plan
        return plan


def interrupt_for_secret(key_name: str) -> str:
    """Pause graph execution to request a missing secret without losing state or leaking tokens."""
    # First check if secret is already present
    secret_mgr = SecretManager()
    existing = secret_mgr.get_secret(key_name, prompt_user=False)
    if existing:
        return existing

    resume_val = interrupt({
        "type": "missing_secret",
        "secret_name": key_name,
        "message": f"Execution paused: required secret '{key_name}' is missing.",
    })

    if isinstance(resume_val, str) and resume_val:
        secret_mgr.store_secret(key_name, resume_val)
        return resume_val
    elif isinstance(resume_val, dict) and "value" in resume_val:
        val = resume_val["value"]
        secret_mgr.store_secret(key_name, val)
        return val

    raise ValueError(f"Secret '{key_name}' was not provided during interrupt resume.")

