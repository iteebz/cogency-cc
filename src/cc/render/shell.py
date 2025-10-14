"""Shell output rendering utilities."""

import re

from .color import C


def format_shell_output(content: str, exit_code: int = 0) -> str:
    """Format shell command output with appropriate styling.

    Args:
        content: The shell command output
        exit_code: The command's exit code

    Returns:
        Formatted output with ANSI color codes
    """
    if not content:
        return ""

    lines = content.split("\n")
    formatted_lines = []

    # Apply color based on exit code
    prefix = f"{C.GREEN}" if exit_code == 0 else f"{C.RED}"

    for line in lines:
        if not line.strip():
            formatted_lines.append(line)
            continue

        # Highlight common patterns
        line = _highlight_patterns(line)
        formatted_lines.append(f"{prefix}{line}{C.R}")

    return "\n".join(formatted_lines)


def _highlight_patterns(line: str) -> str:
    """Apply syntax highlighting to common shell patterns."""
    # File paths
    line = re.sub(r"(/[^\s]+)", f"{C.CYAN}\\1{C.R}", line)

    # URLs
    line = re.sub(r"(https?://[^\s]+)", f"{C.BLUE}\\1{C.R}", line)

    # Error patterns
    if re.search(r"\b(error|failed|failure|exception|traceback)\b", line, re.IGNORECASE):
        line = f"{C.RED}{line}{C.R}"

    # Warning patterns
    elif re.search(r"\b(warn|warning|caution)\b", line, re.IGNORECASE):
        line = f"{C.YELLOW}{line}{C.R}"

    # Success patterns
    elif re.search(r"\b(success|done|completed|finished)\b", line, re.IGNORECASE):
        line = f"{C.GREEN}{line}{C.R}"

    return line
