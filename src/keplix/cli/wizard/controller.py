"""Central Wizard Controller orchestrating Steps 0–4 of the Keplix init wizard."""

from collections.abc import Callable
from typing import Any, Optional

from keplix.cli.wizard.context import SetupContext
from keplix.cli.wizard.step0_welcome import run_step0_welcome
from keplix.cli.wizard.step1_env import run_step1_environment
from keplix.cli.wizard.step2_workspace import run_step2_workspace
from keplix.cli.wizard.step3_domains import run_step3_domains
from keplix.cli.wizard.step4_permissions import run_step4_permissions
from keplix.cli.wizard.ui import NAV_BACK, WizardCancelledException, console

StepRunner = Callable[[SetupContext], Any]

# Clean extensible registry of wizard steps (no sprawling if/else ladders)
DEFAULT_STEPS: list[StepRunner] = [
    run_step0_welcome,       # Step 0: Welcome banner
    run_step1_environment,   # Step 1: System & environment checks
    run_step2_workspace,     # Step 2: Workspace directory selection
    run_step3_domains,       # Step 3: Project domains selection
    run_step4_permissions,   # Step 4: Capabilities and permissions
]


class WizardController:
    """Manages state transitions and bidirectional flow across wizard stages."""

    def __init__(self, steps: Optional[list[StepRunner]] = None, total_steps: int = 9) -> None:
        self.steps = steps or DEFAULT_STEPS
        self.total_steps = total_steps

    def execute(self, initial_step: int = 0) -> SetupContext:
        """Execute the interactive wizard through registered stages.

        Supports bidirectional step navigation (forward/back) and graceful cancellation.

        Returns:
            Populated SetupContext on success.

        Raises:
            WizardCancelledException if user cancels the setup.
        """
        context = SetupContext(total_steps=self.total_steps)
        step_idx = initial_step

        try:
            while 0 <= step_idx < len(self.steps):
                context.current_step = step_idx
                step_func = self.steps[step_idx]

                result = step_func(context)

                # Back navigation handling
                if result is False or result == NAV_BACK:
                    if step_idx == 0:
                        # Backing out of welcome screen terminates setup cleanly
                        break
                    step_idx -= 1
                else:
                    step_idx += 1

            return context

        except (WizardCancelledException, KeyboardInterrupt):
            context.cancelled = True
            raise WizardCancelledException("Setup cancelled by user.")


def run_init_wizard(total_steps: int = 9) -> Optional[SetupContext]:
    """Public entrypoint to launch the Keplix init wizard.

    Returns:
        SetupContext if completed, or None if cancelled.
    """
    controller = WizardController(total_steps=total_steps)
    try:
        return controller.execute()
    except WizardCancelledException:
        console.print("\n[dim]Keplix setup was cancelled. No changes were made.[/dim]\n")
        return None
