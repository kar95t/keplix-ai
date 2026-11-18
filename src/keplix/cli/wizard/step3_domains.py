"""Step 3: Domain pack selection for Keplix CLI First-Run Setup."""

from typing import Any

from keplix.cli.wizard.context import SetupContext
from keplix.cli.wizard.ui import (
    NAV_BACK,
    prompt_two_column_domains,
)
from keplix.config.settings import DomainConfig, DomainMode

# ---------------------------------------------------------------------------
# Registered Domain Packs (matching reference design Image 1)
# ---------------------------------------------------------------------------

DOMAIN_PACKS: list[dict[str, Any]] = [
    {
        "id": "software",
        "title": "Software & Engineering",
        "description": "Code synthesis, refactoring, AST analysis, CI/CD, Git workflows",
        "default": True,
    },
    {
        "id": "marketing",
        "title": "Marketing & Growth",
        "description": "SEO, copy generation, campaign analytics, growth experiments",
        "default": False,
    },
    {
        "id": "content",
        "title": "Writing & Content",
        "description": "Technical writing, documentation, blogs, publishing pipelines",
        "default": False,
    },
    {
        "id": "creative",
        "title": "Creative & Design",
        "description": "UI/UX specifications, design tokens, asset generation",
        "default": False,
    },
    {
        "id": "finance",
        "title": "Finance & Accounting",
        "description": "Financial modeling, budget tracking, ledger validations",
        "default": False,
    },
    {
        "id": "data_analytics",
        "title": "Data & Analytics",
        "description": "SQL queries, data pipelines, pandas/polars analysis, visualization",
        "default": False,
    },
    {
        "id": "business",
        "title": "Business & Strategy",
        "description": "Business plans, market research, competitive analysis",
        "default": False,
    },
    {
        "id": "operations",
        "title": "Operations & Automation",
        "description": "Infrastructure as code, task automation, runbooks, monitoring",
        "default": False,
    },
    {
        "id": "research",
        "title": "Research & Knowledge",
        "description": "Deep literature reviews, paper synthesis, knowledge graphs",
        "default": False,
    },
]


def run_step3_domains(context: SetupContext) -> bool:
    """Execute Step 3 — Domain Pack Selection.

    Presents a side-by-side reactive two-column layout matching Image 1:
    - Left column: Automatic domain detection, Select domain packs manually, General / Core only.
    - Right column: Checkbox list of 9 domain packs with dynamic count preview.

    Args:
        context: Shared in-memory SetupContext holding wizard state.

    Returns:
        True to advance to Step 4.
        False to navigate back to Step 2.
    """
    # Determine initial mode & selections from existing context if any
    default_mode = "auto"
    default_selected = None
    if context.domains:
        if context.domains.mode == DomainMode.SPECIALIZED:
            default_mode = "manual"
            default_selected = context.domains.enabled
        elif context.domains.mode == DomainMode.CORE_ONLY:
            default_mode = "core_only"
            default_selected = []
        elif context.domains.mode == DomainMode.AUTO:
            default_mode = "auto"

    mode_choice, enabled_domains = prompt_two_column_domains(
        domain_packs=DOMAIN_PACKS,
        current_step=3,
        total_steps=context.total_steps,
        default_mode=default_mode,
        default_selected=default_selected,
        allow_back=True,
    )

    if mode_choice == NAV_BACK:
        return False

    if mode_choice == "auto":
        context.domains = DomainConfig(
            mode=DomainMode.AUTO,
            enabled=enabled_domains,
        )
    elif mode_choice == "manual":
        context.domains = DomainConfig(
            mode=DomainMode.SPECIALIZED,
            enabled=enabled_domains,
        )
    elif mode_choice == "core_only":
        context.domains = DomainConfig(
            mode=DomainMode.CORE_ONLY,
            enabled=[],
        )

    return True
