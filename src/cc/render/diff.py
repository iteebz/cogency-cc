"""Diff rendering."""

from .color import C


def render_diff(diff: str) -> list[str]:
    """Parse unified diff into colored lines."""
    if not diff.strip():
        return []

    lines = []
    for line in diff.split("\n"):
        if line.startswith("---") or line.startswith("+++"):
            lines.append(f"{C.GRAY}{line}{C.R}")
        elif line.startswith("@@"):
            lines.append(f"{C.CYAN}{line}{C.R}")
        elif line.startswith("+"):
            lines.append(f"{C.GREEN}{line}{C.R}")
        elif line.startswith("-"):
            lines.append(f"{C.RED}{line}{C.R}")
        else:
            lines.append(line)
    return lines
