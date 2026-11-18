"""Rich UI components, color themes, badges, and keyboard-driven prompts for the wizard."""

from collections.abc import Callable
import os
from pathlib import Path
import sys
import time
from typing import Any, Optional

import re

try:
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree
    console = Console(highlight=False)
    err_console = Console(stderr=True, highlight=False)
except ImportError:
    # Standard library fallback when Rich is not installed
    class Text:  # type: ignore[no-redef]
        def __init__(self, text: str = "", style: str = "") -> None:
            self.plain = text
            self.markup = text
        @classmethod
        def from_markup(cls, text: str) -> "Text":
            return cls(text)
        def append(self, text: str, style: str = "") -> None:
            self.plain += text
            self.markup += text
        def __str__(self) -> str:
            return self.markup

    class Panel:  # type: ignore[no-redef]
        def __init__(self, renderable: Any, border_style: str = "", padding: Any = None, expand: bool = False, title: str = "") -> None:
            self.renderable = renderable
            self.title = title
        def __str__(self) -> str:
            lines = str(self.renderable).splitlines()
            width = max(len(l) for l in lines) + 4 if lines else 20
            top = "┌" + "─" * (width - 2) + "┐"
            bot = "└" + "─" * (width - 2) + "┘"
            mid = [f"│ {l.ljust(width - 4)} │" for l in lines]
            return "\n".join([top] + mid + [bot])

    class Table:  # type: ignore[no-redef]
        @classmethod
        def grid(cls, padding: Any = None) -> "Table":
            return cls()
        def add_column(self, *args: Any, **kwargs: Any) -> None:
            pass
        def add_row(self, *args: Any, **kwargs: Any) -> None:
            pass

    class Tree:  # type: ignore[no-redef]
        def __init__(self, label: str) -> None:
            self.label = label
        def add(self, label: str) -> "Tree":
            return self

    class Group:  # type: ignore[no-redef]
        def __init__(self, *renderables: Any) -> None:
            self.renderables = renderables
        def __str__(self) -> str:
            return "\n".join(str(r) for r in self.renderables)

    class Live:  # type: ignore[no-redef]
        def __init__(self, renderable: Any, *args: Any, **kwargs: Any) -> None:
            self.renderable = renderable
            self._console = kwargs.get("console", console)
            self._transient = kwargs.get("transient", False)
            self._lines = 0
        def __enter__(self) -> "Live":
            self._print()
            return self
        def __exit__(self, *args: Any) -> None:
            if self._transient and self._lines > 0:
                sys.stdout.write(f"\033[{self._lines}A\033[J")
                sys.stdout.flush()
        def _print(self) -> None:
            s = str(self.renderable)
            self._lines = len(s.splitlines())
            self._console.print(self.renderable)
        def update(self, renderable: Any, refresh: bool = True) -> None:
            if self._lines > 0:
                sys.stdout.write(f"\033[{self._lines}A\033[J")
                sys.stdout.flush()
            self.renderable = renderable
            if refresh:
                self._print()

    class Console:  # type: ignore[no-redef]
        def __init__(self, stderr: bool = False, highlight: bool = False) -> None:
            self._file = sys.stderr if stderr else sys.stdout
        def print(self, *args: Any, **kwargs: Any) -> None:
            cleaned = []
            for a in args:
                s = str(a)
                s = re.sub(r"\[/?(?:bold|dim|italic|underline|black|white|red|green|yellow|blue|magenta|cyan|[#0-9a-fA-F]+)(?:[^\]]*)\]", "", s)
                cleaned.append(s)
            print(*cleaned, file=self._file, **kwargs)
        def clear(self) -> None:
            pass
        def show_cursor(self, show: bool) -> None:
            pass

    console = Console(highlight=False)
    err_console = Console(stderr=True, highlight=False)

# Theme Palette (Purple/Magenta primary, Cyan secondary, Green success, Yellow warn, Red error)
CLR_PURPLE = "#c084fc"
CLR_PURPLE_DARK = "#7e22ce"
CLR_CYAN = "#38bdf8"
CLR_GREEN = "#22c55e"
CLR_YELLOW = "#f59e0b"
CLR_RED = "#ef4444"
CLR_DIM = "#94a3b8"
CLR_DARK_BG = "#0f172a"

# Sentinel return values for navigation
NAV_BACK = "__NAV_BACK__"
NAV_CANCEL = "__NAV_CANCEL__"


class WizardCancelledException(Exception):
    """Raised when the user cancels the wizard at any stage."""
    pass


def clear_screen() -> None:
    """Clear terminal screen and scrollback history buffer cleanly cross-platform."""
    try:
        if sys.platform == "win32":
            os.system("cls")
        else:
            sys.stdout.write("\033[H\033[2J\033[3J")
            sys.stdout.flush()
    except Exception:
        console.clear()


# ---------------------------------------------------------------------------
# Path and Formatting Helpers
# ---------------------------------------------------------------------------

def format_path_display(path: Path) -> str:
    """Format path for friendly display, replacing home directory with ~."""
    try:
        resolved = path.resolve()
        home = Path.home().resolve()
        try:
            rel = resolved.relative_to(home)
            # Use forward slashes for clean modern display as in screenshots
            return f"~/{rel.as_posix()}"
        except ValueError:
            return resolved.as_posix()
    except Exception:
        return str(path)


# ---------------------------------------------------------------------------
# Badges and Indicators
# ---------------------------------------------------------------------------

def badge_recommended() -> str:
    return f"[bold {CLR_GREEN} on black] RECOMMENDED [/bold {CLR_GREEN} on black]"


def badge_stable() -> str:
    return f"[bold {CLR_CYAN} on black] STABLE [/bold {CLR_CYAN} on black]"


def badge_experimental() -> str:
    return f"[bold {CLR_PURPLE} on black] EXPERIMENTAL [/bold {CLR_PURPLE} on black]"


def badge_not_recommended() -> str:
    return f"[bold {CLR_RED} on black] NOT RECOMMENDED [/bold {CLR_RED} on black]"


def get_badge_markup(badge_name: str) -> str:
    b = badge_name.upper().strip()
    if b == "RECOMMENDED":
        return badge_recommended()
    if b == "STABLE":
        return badge_stable()
    if b == "EXPERIMENTAL":
        return badge_experimental()
    if b in ("NOT RECOMMENDED", "NOT_RECOMMENDED"):
        return badge_not_recommended()
    return f"[{CLR_DIM}][{b}][/{CLR_DIM}]"


# ---------------------------------------------------------------------------
# Header and Progress Component (Configurable Stages 0-8)
# ---------------------------------------------------------------------------

def build_wizard_header(
    current_step: int,
    total_steps: int = 9,
    completed_steps: Optional[set[int]] = None,
) -> Group:
    """Build the wizard header bar with stage counter and circle progress indicators."""
    completed = completed_steps or set()

    # Left: Setup Wizard (X/Total)
    left_text = Text()
    left_text.append(f"Setup Wizard ({current_step}/{total_steps})", style=f"bold {CLR_DIM}")

    # Right: Step circles (1) ── (2) ── (3) ...
    circles_text = Text()
    num_displayed_steps = min(total_steps - 1, 6)

    for step_num in range(1, num_displayed_steps + 1):
        if step_num in completed or (step_num < current_step):
            circles_text.append("(✔)", style=f"bold {CLR_GREEN}")
        elif step_num == current_step:
            circles_text.append(f"({step_num})", style=f"bold white on {CLR_PURPLE_DARK}")
        else:
            circles_text.append(f"({step_num})", style=f"dim {CLR_DIM}")

        if step_num < num_displayed_steps:
            circles_text.append(" ── ", style=f"dim {CLR_DIM}")

    header_line = f"  {left_text.markup}{' ' * max(2, 40 - len(left_text.plain))} {circles_text.markup}"
    return Group(
        Text(""),
        Text.from_markup(header_line),
        Text(""),
    )


def render_wizard_header(
    current_step: int,
    total_steps: int = 9,
    completed_steps: Optional[set[int]] = None,
) -> None:
    """Render the wizard header bar with stage counter and circle progress indicators."""
    console.print(build_wizard_header(current_step, total_steps, completed_steps))


def build_step_title(icon: str, step_label: str, subtitle: Optional[str] = None) -> Group:
    """Build consistent step title and optional subtitle as a Rich Group."""
    lines: list[Any] = [Text.from_markup(f"  {icon} [bold {CLR_PURPLE}]{step_label}[/bold {CLR_PURPLE}]")]
    if subtitle:
        lines.append(Text.from_markup(f"  [dim {CLR_DIM}]{subtitle}[/dim {CLR_DIM}]"))
    lines.append(Text(""))
    return Group(*lines)


def render_step_title(icon: str, step_label: str, subtitle: Optional[str] = None) -> None:
    """Render consistent step title and optional subtitle."""
    console.print(build_step_title(icon, step_label, subtitle))


def build_step_pill_header(
    current_step: int,
    total_steps: int = 9,
    step_name: str = "",
    left_title: str = "keplix init",
) -> Group:
    """Build the modern step header bar matching the UI reference designs."""
    pill = f"[bold white on {CLR_PURPLE_DARK}] {current_step}/{total_steps} [/bold white on {CLR_PURPLE_DARK}]  [bold {CLR_PURPLE}]{step_name}[/bold {CLR_PURPLE}]"

    # Segmented progress bar (e.g. ▰▰▰▱▱▱▱▱▱)
    segments = []
    for s in range(1, total_steps + 1):
        if s <= current_step:
            segments.append(f"[bold {CLR_PURPLE}]▰[/bold {CLR_PURPLE}]")
        else:
            segments.append(f"[{CLR_DIM}]▱[/{CLR_DIM}]")
    prog_bar = " ".join(segments)

    header_line = f"  [bold {CLR_DIM}]{left_title}[/bold {CLR_DIM}]{' ' * max(2, 42 - len(left_title))} {pill}"
    prog_line = f"  {prog_bar}"
    return Group(
        Text(""),
        Text.from_markup(header_line),
        Text.from_markup(prog_line),
        Text(""),
    )


def render_step_pill_header(
    current_step: int,
    total_steps: int = 9,
    step_name: str = "",
    left_title: str = "keplix init",
) -> None:
    """Render the modern step header bar matching the UI reference designs.

    Features window title, step pill badge, and segmented progress bar.
    """
    console.print(build_step_pill_header(current_step, total_steps, step_name, left_title))


def render_info_panel(message: str) -> None:
    """Render an informational callout panel matching Image 1 with an (i) icon."""
    body = f"[bold {CLR_PURPLE}](i)[/bold {CLR_PURPLE}]  [dim {CLR_DIM}]{message}[/dim {CLR_DIM}]"
    panel = Panel(body, border_style=CLR_PURPLE, padding=(0, 1), expand=False)
    console.print(panel)
    console.print()


# ---------------------------------------------------------------------------
# Welcome Screen Brand Banner (Option A: Isometric Orbit Cube + Block Font)
# ---------------------------------------------------------------------------

KEPLIX_BANNER_OPTION_A = (
    f"[bold {CLR_PURPLE}]       ╭───╮[/bold {CLR_PURPLE}]   [bold {CLR_CYAN}]█  █  █▀▀▀  █▀▀█  █     ▀█▀  █  █[/bold {CLR_CYAN}]\n"
    f"[bold {CLR_PURPLE}]      ╱   ╱│[/bold {CLR_PURPLE}]   [bold {CLR_CYAN}]█▄▀   █▄▄   █▄▄█  █      █    ▀▄▀ [/bold {CLR_CYAN}]\n"
    f"[bold {CLR_PURPLE}]     ╭───╮ │[/bold {CLR_PURPLE}]   [bold {CLR_CYAN}]█  █  █▄▄▄  █     █▄▄▄  ▄█▄  █  █[/bold {CLR_CYAN}]\n"
    f"[bold {CLR_PURPLE}]     │   │ ╯[/bold {CLR_PURPLE}]\n"
    f"[bold {CLR_PURPLE}]     ╰───╯[/bold {CLR_PURPLE}]     [dim]Your AI coding workforce, orchestrated.[/dim]"
)

KEPLIX_ASCII_LOGO = (
    "       ╭───╮   █  █  █▀▀▀  █▀▀█  █     ▀█▀  █  █\n"
    "      ╱   ╱│   █▄▀   █▄▄   █▄▄█  █      █    ▀▄▀ \n"
    "     ╭───╮ │   █  █  █▄▄▄  █     █▄▄▄  ▄█▄  █  █\n"
    "     │   │ ╯\n"
    "     ╰───╯     Your AI coding workforce, orchestrated."
)


def render_keplix_brand_banner() -> None:
    """Render the official Keplix ASCII logo banner and tagline (Option A)."""
    console.print()
    console.print(KEPLIX_BANNER_OPTION_A)
    console.print()


def build_keplix_brand_banner() -> Group:
    """Build the official Keplix ASCII logo banner and tagline renderable (Option A)."""
    return Group(
        Text(""),
        Text.from_markup(KEPLIX_BANNER_OPTION_A),
        Text(""),
    )


# ---------------------------------------------------------------------------
# Cross-Platform Keyboard Input & Navigation
# ---------------------------------------------------------------------------

def _get_key_non_blocking() -> Optional[str]:
    """Read a single keypress if available; return None immediately if no input is pending."""
    if sys.platform == "win32":
        import msvcrt
        if not msvcrt.kbhit():
            return None
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            # Special arrow keys on Windows
            sub = msvcrt.getch()
            if sub == b"H":
                return "UP"
            elif sub == b"P":
                return "DOWN"
            elif sub == b"K":
                return "LEFT"
            elif sub == b"M":
                return "RIGHT"
            return "SPECIAL"
        if ch == b"\r" or ch == b"\n":
            return "ENTER"
        if ch == b"\x1b":
            return "ESC"
        if ch in (b" ", b"\x20"):
            return "SPACE"
        if ch in (b"\t", b"\x09"):
            return "TAB"
        if ch == b"\x03":
            raise KeyboardInterrupt()
        try:
            return ch.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    else:
        # Unix / macOS
        import select
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if not dr:
            return None
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # Check for escape sequence
                dr2, _, _ = select.select([sys.stdin], [], [], 0.05)
                if dr2:
                    next1 = sys.stdin.read(1)
                    if next1 == "[":
                        next2 = sys.stdin.read(1)
                        if next2 == "A":
                            return "UP"
                        elif next2 == "B":
                            return "DOWN"
                        elif next2 == "C":
                            return "RIGHT"
                        elif next2 == "D":
                            return "LEFT"
                return "ESC"
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch == " ":
                return "SPACE"
            if ch == "\t":
                return "TAB"
            if ch == "\x03":
                raise KeyboardInterrupt()
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _get_key() -> str:
    """Read a single keypress, waiting until one is available."""
    while True:
        k = _get_key_non_blocking()
        if k is not None:
            return k
        time.sleep(0.04)


# ---------------------------------------------------------------------------
# Interactive Menu Selector (Driven by Rich Live Display)
# ---------------------------------------------------------------------------

def _build_menu_group(
    title: Optional[str],
    options: list[dict[str, Any]],
    selected_idx: int,
    allow_back: bool = True,
    header_renderable: Optional[Any] = None,
) -> Group:
    """Build the Rich Group renderable for the interactive menu."""
    items: list[Any] = []
    if header_renderable:
        items.append(header_renderable)

    if title:
        items.append(Text(f"  {title}", style="bold"))
        items.append(Text(""))

    for i, opt in enumerate(options):
        is_selected = (i == selected_idx)
        num_label = f"{i + 1}."

        badges_markup = "  ".join(get_badge_markup(b) for b in opt.get("badges", []))
        badges_str = f"  {badges_markup}" if badges_markup else ""

        if is_selected:
            # Highlighted panel matching the reference screenshot
            body_text = f"[bold {CLR_PURPLE}]> {num_label}[/bold {CLR_PURPLE}] [bold white]{opt['title']}[/bold white]{badges_str}"
            if opt.get("description"):
                body_text += f"\n     [dim {CLR_DIM}]{opt['description']}[/dim {CLR_DIM}]"

            panel = Panel(
                Text.from_markup(body_text, overflow="fold") if hasattr(Text, "from_markup") else body_text,
                border_style=CLR_PURPLE,
                padding=(0, 1),
                expand=False,
            )
            items.append(panel)
        else:
            text_str = f"    {num_label} {opt['title']}{badges_str}"
            if opt.get("description"):
                text_str += f"\n       [dim {CLR_DIM}]{opt['description']}[/dim {CLR_DIM}]"
            items.append(Text.from_markup(text_str, overflow="fold") if hasattr(Text, "from_markup") else text_str)

    # Footer hint
    footer_hint = "  [dim]↑ ↓ to navigate • Enter to select"
    if allow_back:
        footer_hint += " • Esc to go back"
    footer_hint += "[/dim]"
    items.append(Text(""))
    items.append(Text.from_markup(footer_hint) if hasattr(Text, "from_markup") else footer_hint)

    return Group(*items)


def prompt_select(
    title: Optional[str],
    options: list[dict[str, Any]],
    default_idx: int = 0,
    allow_back: bool = True,
    clear_after: bool = False,
    header_renderable: Optional[Any] = None,
) -> Any:
    """Render an interactive keyboard-driven menu matching the reference design.

    Each option in options is a dict:
      {
        "id": Any,
        "title": str,
        "description": Optional[str],
        "badges": list[str]  # e.g. ["RECOMMENDED", "STABLE"]
      }

    Returns selected option's 'id', or NAV_BACK if Esc is pressed, or raises WizardCancelledException.
    Falls back gracefully to numbered plain-text input in non-interactive/testing environments.
    """
    if not options:
        return None

    # Check if stdin is a live interactive terminal
    is_interactive = sys.stdin.isatty() and not os.getenv("KEPLIX_TEST_NON_INTERACTIVE")

    if not is_interactive:
        # Non-interactive / piped / testing fallback
        if header_renderable:
            console.print(header_renderable)
        if title:
            console.print(f"  [bold]{title}[/bold]")
        for i, opt in enumerate(options, 1):
            badges_str = " ".join(get_badge_markup(b) for b in opt.get("badges", []))
            console.print(f"  {i}. {opt['title']} {badges_str}")
            if opt.get("description"):
                console.print(f"     [dim]{opt['description']}[/dim]")

        hint = "↑/↓ to navigate • Enter to select"
        if allow_back:
            hint += " • 'b' to go back"
        hint += " • 'q' to cancel"
        console.print(f"  [dim]{hint}[/dim]")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    # EOF encountered
                    return options[default_idx]["id"]
                val = line.strip()
                if not val:
                    return options[default_idx]["id"]
                if val.lower() in ("q", "quit", "cancel"):
                    raise WizardCancelledException()
                if allow_back and val.lower() in ("b", "back", "esc"):
                    return NAV_BACK
                if val.isdigit():
                    num = int(val)
                    if 1 <= num <= len(options):
                        return options[num - 1]["id"]
                # Match by title or id
                for opt in options:
                    if str(opt["id"]) == val or opt["title"].lower() == val.lower():
                        return opt["id"]
                console.print(f"  [red]Please enter a valid choice (1-{len(options)}):[/red] ", end="")
            except (KeyboardInterrupt, EOFError):
                raise WizardCancelledException()

    # Interactive keyboard-driven loop using Rich Live display in Alternate Screen Buffer
    selected = default_idx
    num_options = len(options)
    last_size = console.size

    menu_group = _build_menu_group(title, options, selected, allow_back, header_renderable)
    with Live(menu_group, console=console, screen=True, auto_refresh=False) as live:
        while True:
            current_size = console.size
            if current_size != last_size:
                last_size = current_size
                live.update(_build_menu_group(title, options, selected, allow_back, header_renderable), refresh=True)

            try:
                key = _get_key_non_blocking()
            except KeyboardInterrupt:
                raise WizardCancelledException()

            if key is None:
                time.sleep(0.04)
                continue

            if key == "UP":
                selected = (selected - 1) % num_options
                live.update(_build_menu_group(title, options, selected, allow_back, header_renderable), refresh=True)
            elif key == "DOWN":
                selected = (selected + 1) % num_options
                live.update(_build_menu_group(title, options, selected, allow_back, header_renderable), refresh=True)
            elif key == "ENTER":
                return options[selected]["id"]
            elif key == "ESC" and allow_back:
                return NAV_BACK
            elif key.isdigit():
                idx = int(key) - 1
                if 0 <= idx < num_options:
                    selected = idx
                    live.update(_build_menu_group(title, options, selected, allow_back, header_renderable), refresh=True)


# ---------------------------------------------------------------------------
# Interactive Multi-Select Checklist (Driven by Rich Live Display)
# ---------------------------------------------------------------------------

def _build_multi_select_group(
    title: Optional[str],
    items: list[dict[str, Any]],
    selected_idx: int,
    checked_set: set[str],
    allow_back: bool = True,
    item_label: str = "domains",
) -> Group:
    """Build the Rich Group renderable for the interactive multi-select checklist."""
    render_items: list[Any] = []
    if title:
        render_items.append(Text(f"  {title}", style="bold white"))
        render_items.append(Text(""))

    for i, item in enumerate(items):
        is_focused = (i == selected_idx)
        is_checked = (item["id"] in checked_set)

        # Checkbox symbol matching reference design
        if is_checked:
            box_markup = f"[bold {CLR_GREEN}][✔][/bold {CLR_GREEN}]"
        else:
            box_markup = f"[{CLR_DIM}][ ][/{CLR_DIM}]"

        badges_markup = "  ".join(get_badge_markup(b) for b in item.get("badges", []))
        badges_str = f"  {badges_markup}" if badges_markup else ""

        if is_focused:
            row_text = f"[bold {CLR_PURPLE}]>[/bold {CLR_PURPLE}] {box_markup} [bold white]{item['title']}[/bold white]{badges_str}"
            if item.get("description"):
                row_text += f"\n     [dim {CLR_DIM}]{item['description']}[/dim {CLR_DIM}]"
            panel = Panel(
                row_text,
                border_style=CLR_PURPLE,
                padding=(0, 1),
                expand=False,
            )
            render_items.append(panel)
        else:
            row_text = f"    {box_markup} {item['title']}{badges_str}"
            if item.get("description"):
                row_text += f"\n       [dim {CLR_DIM}]{item['description']}[/dim {CLR_DIM}]"
            render_items.append(Text.from_markup(row_text) if hasattr(Text, "from_markup") else row_text)

    # Dynamic counter line matching Image 1: "X domains selected"
    count_str = f"  [bold {CLR_CYAN}]{len(checked_set)}[/bold {CLR_CYAN}] [dim]{item_label} selected[/dim]"
    render_items.append(Text(""))
    render_items.append(Text.from_markup(count_str) if hasattr(Text, "from_markup") else count_str)

    # Footer navigation hints
    hint = "  [dim]↑ ↓ to navigate • Space to toggle • 'a' all • 'n' none • Enter to confirm"
    if allow_back:
        hint += " • Esc to go back"
    hint += "[/dim]"
    render_items.append(Text.from_markup(hint) if hasattr(Text, "from_markup") else hint)

    return Group(*render_items)


def prompt_multi_select(
    title: Optional[str],
    items: list[dict[str, Any]],
    default_selected: Optional[list[str]] = None,
    allow_back: bool = True,
    clear_after: bool = False,
    item_label: str = "domains",
) -> Any:
    """Render an interactive checklist allowing multiple item selections.

    Returns list of selected item IDs, or NAV_BACK if Esc pressed.
    """
    if not items:
        return []

    checked_set = set(default_selected or [])
    is_interactive = sys.stdin.isatty() and not os.getenv("KEPLIX_TEST_NON_INTERACTIVE")

    if not is_interactive:
        # Non-interactive / piped fallback
        if title:
            console.print(f"  [bold]{title}[/bold]")
        for i, item in enumerate(items, 1):
            mark = "[✔]" if item["id"] in checked_set else "[ ]"
            console.print(f"  {i}. {mark} {item['title']}")
        console.print(f"  [dim]Enter numbers (comma-separated, e.g. 1,2), 'all', 'none', or Enter to accept ({len(checked_set)} selected):[/dim] ", end="")
        try:
            line = sys.stdin.readline()
            if not line:
                return [it["id"] for it in items if it["id"] in checked_set]
            val = line.strip().lower()
            if not val:
                return [it["id"] for it in items if it["id"] in checked_set]
            if val in ("q", "quit", "cancel"):
                raise WizardCancelledException()
            if allow_back and val in ("b", "back", "esc"):
                return NAV_BACK
            if val in ("all", "a"):
                return [it["id"] for it in items]
            if val in ("none", "n"):
                return []
            nums = [s.strip() for s in val.split(",") if s.strip().isdigit()]
            if nums:
                res = []
                for n in nums:
                    idx = int(n) - 1
                    if 0 <= idx < len(items):
                        res.append(items[idx]["id"])
                return res
            return [it["id"] for it in items if it["id"] in checked_set]
        except (KeyboardInterrupt, EOFError):
            raise WizardCancelledException()

    # Interactive loop using Rich Live in Alternate Screen Buffer
    selected = 0
    num_items = len(items)
    last_size = console.size

    group = _build_multi_select_group(title, items, selected, checked_set, allow_back, item_label)
    with Live(group, console=console, screen=True, auto_refresh=False) as live:
        while True:
            current_size = console.size
            if current_size != last_size:
                last_size = current_size
                live.update(_build_multi_select_group(title, items, selected, checked_set, allow_back, item_label), refresh=True)

            try:
                key = _get_key_non_blocking()
            except KeyboardInterrupt:
                raise WizardCancelledException()

            if key is None:
                time.sleep(0.04)
                continue

            if key == "UP":
                selected = (selected - 1) % num_items
                live.update(_build_multi_select_group(title, items, selected, checked_set, allow_back, item_label), refresh=True)
            elif key == "DOWN":
                selected = (selected + 1) % num_items
                live.update(_build_multi_select_group(title, items, selected, checked_set, allow_back, item_label), refresh=True)
            elif key in (" ", "SPACE"):
                current_id = items[selected]["id"]
                if current_id in checked_set:
                    checked_set.remove(current_id)
                else:
                    checked_set.add(current_id)
                live.update(_build_multi_select_group(title, items, selected, checked_set, allow_back, item_label), refresh=True)
            elif key in ("a", "A"):
                checked_set = {it["id"] for it in items}
                live.update(_build_multi_select_group(title, items, selected, checked_set, allow_back, item_label), refresh=True)
            elif key in ("n", "N"):
                checked_set.clear()
                live.update(_build_multi_select_group(title, items, selected, checked_set, allow_back, item_label), refresh=True)
            elif key == "ENTER":
                return [it["id"] for it in items if it["id"] in checked_set]
            elif key == "ESC" and allow_back:
                return NAV_BACK
            elif key.isdigit():
                idx = int(key) - 1
                if 0 <= idx < num_items:
                    current_id = items[idx]["id"]
                    if current_id in checked_set:
                        checked_set.remove(current_id)
                    else:
                        checked_set.add(current_id)
                    selected = idx
                    live.update(_build_multi_select_group(title, items, selected, checked_set, allow_back, item_label), refresh=True)


# ---------------------------------------------------------------------------
# Simple Prompts (Press Enter, Text Input)
# ---------------------------------------------------------------------------

def prompt_press_enter(message: str = "Press Enter to continue...") -> None:
    """Prompt user to press Enter to advance. Handles Ctrl+C and non-interactive EOF."""
    console.print()
    console.print(f"  [dim {CLR_CYAN}]{message}[/dim {CLR_CYAN}]", end="")
    sys.stdout.flush()

    if not sys.stdin.isatty():
        try:
            sys.stdin.readline()
        except Exception:
            pass
        console.print()
        return

    try:
        while True:
            key = _get_key()
            if key in ("ENTER", "\r", "\n"):
                break
    except KeyboardInterrupt:
        console.print()
        raise WizardCancelledException()
    console.print()


def prompt_text_input(
    prompt_message: str,
    default: Optional[str] = None,
    validator: Optional[Callable[[str], tuple[bool, str]]] = None,
    allow_back: bool = True,
) -> str:
    """Prompt for text input (e.g. project name or directory path).

    Returns user string, or NAV_BACK if user enters empty input and allow_back is True,
    or raises WizardCancelledException.
    """
    default_str = f" [{default}]" if default else ""

    while True:
        try:
            console.print(f"  [bold white]{prompt_message}[/bold white]{default_str}: ", end="")
            sys.stdout.flush()
            val = sys.stdin.readline()
            if not val:
                # EOF
                if default is not None:
                    return default
                return ""
            clean_val = val.strip()

            if not clean_val:
                if default is not None:
                    return default
                if allow_back:
                    return NAV_BACK
                continue

            if clean_val.lower() in (":back", ":b") and allow_back:
                return NAV_BACK

            if clean_val.lower() in (":quit", ":q", ":cancel"):
                raise WizardCancelledException()

            if validator:
                is_valid, err_msg = validator(clean_val)
                if not is_valid:
                    console.print(f"  [bold {CLR_RED}]✖ {err_msg}[/bold {CLR_RED}]")
                    continue

            return clean_val

        except KeyboardInterrupt:
            console.print()
            raise WizardCancelledException()


# ---------------------------------------------------------------------------
# Step 3: Two-Column Reactive Domain Pack Selector
# ---------------------------------------------------------------------------

STEP3_MODES = [
    {
        "id": "auto",
        "title": "Automatic domain detection",
        "description": "Keplix identifies relevant domains per task\nand loads the right domain packs.",
        "badges": ["RECOMMENDED", "STABLE"],
    },
    {
        "id": "manual",
        "title": "Select domain packs manually",
        "description": "Choose which domains are relevant to this workspace.",
        "badges": [],
    },
    {
        "id": "core_only",
        "title": "General / Core only",
        "description": "Use core capabilities without specialized domain packs.",
        "badges": [],
    },
]

AUTO_DEFAULT_DOMAINS = ["software", "marketing", "content", "data_analytics"]


def _build_two_column_domains_group(
    current_step: int,
    total_steps: int,
    active_col: str,
    mode_idx: int,
    domain_idx: int,
    manual_checked: set[str],
    domain_packs: list[dict[str, Any]],
    allow_back: bool = True,
    width: Optional[int] = None,
) -> Group:
    """Build the Rich Group renderable for the side-by-side 2-column domain selector."""
    items: list[Any] = []

    # 1. Header bar
    items.append(build_step_pill_header(current_step, total_steps, "Project Domains", "keplix init"))

    # 2. Section Title and Subtitle matching Image 1
    items.append(Text.from_markup("  [bold white]What kind of work will you use Keplix for?[/bold white]"))
    items.append(Text.from_markup("  [dim]Select one or more domains, or let Keplix detect automatically.[/dim]\n"))

    # Determine responsive layout mode
    term_width = width or console.width
    is_narrow = term_width < 84

    # Determine effective checked domains for preview
    if mode_idx == 0:
        effective_checked = set(AUTO_DEFAULT_DOMAINS)
    elif mode_idx == 1:
        effective_checked = set(manual_checked)
    else:  # core_only
        effective_checked = set()

    # 3. Left Column: Mode cards
    left_cards: list[Any] = []
    for i, m in enumerate(STEP3_MODES):
        is_mode_selected = (i == mode_idx)
        badges_markup = "  ".join(get_badge_markup(b) for b in m.get("badges", []))
        badges_str = f"  {badges_markup}" if badges_markup else ""

        if is_mode_selected:
            if active_col == "left":
                border_clr = CLR_PURPLE
                radio_markup = f"[bold {CLR_PURPLE}](o)[/bold {CLR_PURPLE}]"
            else:
                border_clr = CLR_CYAN
                radio_markup = f"[bold {CLR_CYAN}](o)[/bold {CLR_CYAN}]"
        else:
            border_clr = CLR_DIM
            radio_markup = f"[{CLR_DIM}]( )[/{CLR_DIM}]"

        card_text = (
            f"{radio_markup} [bold white]{m['title']}[/bold white]{badges_str}\n"
            f"   [dim {CLR_DIM}]{m['description']}[/dim {CLR_DIM}]"
        )
        card_panel = Panel(
            Text.from_markup(card_text, overflow="fold") if hasattr(Text, "from_markup") else card_text,
            border_style=border_clr,
            padding=(0, 1),
            expand=True,
        )
        left_cards.append(card_panel)

    left_group = Group(*left_cards)

    # 4. Right Column: Checkboxes for domain packs
    right_items: list[Any] = []
    for j, d in enumerate(domain_packs):
        is_checked = d["id"] in effective_checked
        box = f"[bold {CLR_GREEN}][✔][/bold {CLR_GREEN}]" if is_checked else f"[{CLR_DIM}][ ][/{CLR_DIM}]"
        is_focused = (active_col == "right" and j == domain_idx)

        if is_focused:
            row_markup = f"[bold {CLR_PURPLE}]>[/bold {CLR_PURPLE}] {box} [bold white]{d['title']}[/bold white]"
        else:
            row_markup = f"  {box} [white]{d['title']}[/white]"

        right_items.append(Text.from_markup(row_markup, overflow="fold"))

    # Dynamic count line matching Image 1
    count_markup = f"\n  [bold {CLR_CYAN}]{len(effective_checked)}[/bold {CLR_CYAN}] [dim]domains selected[/dim]"
    right_items.append(Text.from_markup(count_markup))
    right_group = Group(*right_items)

    # 5. Grid or Stacked combining left and right columns based on breakpoint
    if is_narrow:
        stacked = Table.grid(padding=(0, 1), expand=True)
        stacked.add_column("main", ratio=1)
        stacked.add_row(left_group)
        stacked.add_row(Text(""))
        stacked.add_row(right_group)
        items.append(stacked)
    else:
        grid = Table.grid(padding=(0, 3), expand=True)
        grid.add_column("modes", ratio=6)
        grid.add_column("domains", ratio=5)
        grid.add_row(left_group, right_group)
        items.append(grid)

    # 6. Bottom info panel matching Image 1
    items.append(Text(""))
    info_body = (
        f"[bold {CLR_PURPLE}](i)[/bold {CLR_PURPLE}]  "
        f"[dim]Domain Packs = knowledge, capabilities, tools, task templates and validation policies. "
        f"They enhance Keplix's understanding, not the agent team structure.[/dim]"
    )
    items.append(Panel(Text.from_markup(info_body, overflow="fold"), border_style=CLR_PURPLE, padding=(0, 1), expand=False))

    # 7. Navigation hints
    footer_hint = "  [dim]← → / Tab to switch focus • ↑ ↓ to navigate • Space to toggle • Enter to confirm"
    if allow_back:
        footer_hint += " • Esc to go back"
    footer_hint += "[/dim]"
    items.append(Text.from_markup(footer_hint))

    return Group(*items)


def prompt_two_column_domains(
    domain_packs: list[dict[str, Any]],
    current_step: int = 3,
    total_steps: int = 9,
    default_mode: str = "auto",
    default_selected: Optional[list[str]] = None,
    allow_back: bool = True,
) -> tuple[str, list[str]]:
    """Interactive two-column domain pack selection matching Image 1.

    Returns:
        (mode_id, enabled_domains_list) where mode_id is "auto", "manual", or "core_only",
        or (NAV_BACK, []) if user pressed Esc.
    """
    # Non-interactive fallback
    is_interactive = sys.stdin.isatty() and not os.getenv("KEPLIX_TEST_NON_INTERACTIVE")
    if not is_interactive:
        clear_screen()
        console.print(build_step_pill_header(current_step, total_steps, "Project Domains", "keplix init"))
        console.print("  [bold white]What kind of work will you use Keplix for?[/bold white]")
        for i, m in enumerate(STEP3_MODES, 1):
            console.print(f"  {i}. {m['title']}")
        console.print("  [dim]Enter mode (1=Auto, 2=Manual, 3=Core Only), or Enter for default:[/dim] ", end="")
        try:
            line = sys.stdin.readline().strip()
            if not line or line == "1":
                return "auto", list(AUTO_DEFAULT_DOMAINS)
            if line == "3":
                return "core_only", []
            if line in ("b", "back", "esc"):
                return NAV_BACK, []
            if line in ("q", "quit", "cancel"):
                raise WizardCancelledException()
            return "manual", list(default_selected or ["software"])
        except (KeyboardInterrupt, EOFError):
            raise WizardCancelledException()

    # Interactive keyboard-driven loop in Alternate Screen Buffer
    mode_idx = 0
    if default_mode == "manual":
        mode_idx = 1
    elif default_mode == "core_only":
        mode_idx = 2

    manual_checked: set[str] = set(default_selected if default_selected is not None else AUTO_DEFAULT_DOMAINS)
    active_col = "left"
    domain_idx = 0
    num_domains = len(domain_packs)
    num_modes = len(STEP3_MODES)

    last_size = console.size
    group = _build_two_column_domains_group(
        current_step=current_step,
        total_steps=total_steps,
        active_col=active_col,
        mode_idx=mode_idx,
        domain_idx=domain_idx,
        manual_checked=manual_checked,
        domain_packs=domain_packs,
        allow_back=allow_back,
        width=last_size.columns,
    )

    with Live(group, console=console, screen=True, auto_refresh=False) as live:
        while True:
            current_size = console.size
            if current_size != last_size:
                last_size = current_size
                live.update(
                    _build_two_column_domains_group(
                        current_step=current_step,
                        total_steps=total_steps,
                        active_col=active_col,
                        mode_idx=mode_idx,
                        domain_idx=domain_idx,
                        manual_checked=manual_checked,
                        domain_packs=domain_packs,
                        allow_back=allow_back,
                        width=current_size.columns,
                    ),
                    refresh=True,
                )

            try:
                key = _get_key_non_blocking()
            except KeyboardInterrupt:
                raise WizardCancelledException()

            if key is None:
                time.sleep(0.04)
                continue

            if key == "UP":
                if active_col == "left":
                    mode_idx = (mode_idx - 1) % num_modes
                else:
                    domain_idx = (domain_idx - 1) % num_domains
            elif key == "DOWN":
                if active_col == "left":
                    mode_idx = (mode_idx + 1) % num_modes
                else:
                    domain_idx = (domain_idx + 1) % num_domains
            elif key in ("RIGHT", "TAB") and active_col == "left":
                active_col = "right"
            elif key == "TAB" and active_col == "right":
                active_col = "left"
            elif key == "LEFT" and active_col == "right":
                active_col = "left"
            elif key in (" ", "SPACE"):
                if active_col == "right":
                    cur_id = domain_packs[domain_idx]["id"]
                    if cur_id in manual_checked:
                        manual_checked.remove(cur_id)
                    else:
                        manual_checked.add(cur_id)
                    mode_idx = 1
                elif active_col == "left":
                    if mode_idx == 1:
                        active_col = "right"
            elif key == "ENTER":
                if mode_idx == 0:
                    return "auto", list(AUTO_DEFAULT_DOMAINS)
                elif mode_idx == 1:
                    res = [d["id"] for d in domain_packs if d["id"] in manual_checked]
                    if not res:
                        res = ["software"]
                    return "manual", res
                elif mode_idx == 2:
                    return "core_only", []
            elif key == "ESC" and allow_back:
                return NAV_BACK, []

            live.update(
                _build_two_column_domains_group(
                    current_step=current_step,
                    total_steps=total_steps,
                    active_col=active_col,
                    mode_idx=mode_idx,
                    domain_idx=domain_idx,
                    manual_checked=manual_checked,
                    domain_packs=domain_packs,
                    allow_back=allow_back,
                    width=current_size.columns,
                ),
                refresh=True,
            )


# ---------------------------------------------------------------------------
# Step 4: Permission Action Modal / Selector
# ---------------------------------------------------------------------------

PERMISSION_DESCRIPTIONS = {
    "allow": "Autonomous execution without prompting",
    "approval": "Require explicit confirmation before execution",
    "sandbox": "Run restricted within isolated sandbox boundaries",
    "deny": "Completely disallow this action",
    "allowlist": "Permit outbound connections to approved domains only",
    "disabled": "Completely block external network connections",
    "unrestricted": "Permit all outbound network traffic",
}


def prompt_permission_action(
    action_name: str,
    current_val: str,
    allowed_values: Optional[list[str]] = None,
    allow_back: bool = True,
) -> str:
    """Prompt user to choose an enforcement level (e.g. allow, approval, sandbox, deny).

    Returns selected value string, or current_val if cancelled with Esc.
    """
    if allowed_values is None:
        allowed_values = ["allow", "approval", "sandbox", "deny"]

    options = []
    default_idx = 0
    for idx, val in enumerate(allowed_values):
        is_cur = (val == current_val)
        if is_cur:
            default_idx = idx
        options.append({
            "id": val,
            "title": f"[{CLR_PURPLE}]{val}[/{CLR_PURPLE}]" if is_cur else val,
            "description": PERMISSION_DESCRIPTIONS.get(val, ""),
            "badges": ["CURRENT"] if is_cur else [],
        })

    header_group = Group(
        build_step_pill_header(
            current_step=4,
            total_steps=9,
            step_name="Custom Permissions",
            left_title="Setup Wizard (4/9)",
        ),
        Text.from_markup(f"  [bold white]Configure Permission:[/bold white] [bold {CLR_PURPLE}]{action_name}[/bold {CLR_PURPLE}]"),
        Text.from_markup(f"  [dim]Select the enforcement level for this action (current: [bold {CLR_CYAN}]{current_val}[/bold {CLR_CYAN}]):[/dim]\n"),
    )

    chosen = prompt_select(
        title=None,
        options=options,
        default_idx=default_idx,
        allow_back=allow_back,
        header_renderable=header_group,
    )
    if chosen == NAV_BACK:
        return current_val
    return str(chosen)

