"""Pure formatting functions - no state, no side effects."""

import re

from .color import C


def tool_name(name: str, bold: bool = False) -> str:
    """Extract short name from dotted tool name."""
    if "." in name:
        name = name.split(".")[-1]
    if bold:
        return f"{C.BOLD}{name}{C.R}"
    return name


def tool_arg(args: dict, tool_name: str = "") -> str:
    """Extract primary arg for display."""
    if not isinstance(args, dict):
        return ""

    if tool_name == "find":
        for k in ["content", "pattern"]:
            if v := args.get(k):
                s = str(v)
                return s if len(s) < 50 else s[:47] + "..."
        path = args.get("path", ".")
        return path if path != "." else ""

    if k := next((k for k in ["file", "path"] if k in args), None):
        v = args[k]
        s = str(v)
        if k == "file" or (k == "path" and "." in s.split("/")[-1]):
            s = s.split("/")[-1]
        return s if len(s) < 50 else s[:47] + "..."

    for k in ["pattern", "content", "query", "command", "url"]:
        if v := args.get(k):
            s = str(v)
            return s if len(s) < 50 else s[:47] + "..."

    if args:
        s = str(next(iter(args.values())))
        return s if len(s) < 50 else s[:47] + "..."
    return ""


def tool_outcome(payload: dict) -> str:
    """Format tool result payload into compact outcome."""
    if payload.get("error"):
        return payload.get("outcome", "error")

    outcome = payload.get("outcome", "")
    if not outcome:
        return "ok"

    if m := re.match(r"(Grep|Wrote|Read) .+ \((\d+) lines?\)", outcome):
        return f"{m.group(2)} lines"

    if m := re.match(r"(Edited|Modified) .+ \(([-+0-9/]+)\)", outcome):
        return m.group(2)

    if m := re.match(r"Listed (\d+) items", outcome):
        return f"{m.group(1)} items"

    if m := re.match(r"Found (\d+) (matches|results)", outcome):
        return f"{m.group(1)} {m.group(2)}"

    if m := re.match(r"Command failed \(exit (\d+)\): (.+)", outcome):
        return f"exit {m.group(1)}"

    if m := re.match(r"Command timed out after (\d+) seconds", outcome):
        return "timeout"

    if m := re.match(r"Command not found: (.+)", outcome):
        return "not found"

    return outcome


def format_call(call) -> str:
    """Format tool call for display."""
    name = tool_name(call.name, bold=True)
    arg = tool_arg(call.args)
    return f"{name}({arg}): ..." if arg else f"{name}(): ..."


def format_result(call, payload) -> str:
    """Format tool result for display."""
    name = tool_name(call.name, bold=True)
    arg = tool_arg(call.args)
    outcome = tool_outcome(payload)
    base = f"{name}({arg})" if arg else f"{name}()"
    return f"{base}: {outcome}"


def render_markdown(text: str) -> str:
    """Render markdown with ANSI codes."""
    text = re.sub(r"\*\*(.+?)\*\*", f"{C.BOLD}\\1{C.R}", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)", r"\033[3m\1\033[0m", text)
    text = re.sub(r"`([^`]+)`", f"{C.GRAY}\\1{C.R}", text)
    text = re.sub(r"^(#{1,6})\s+(.+)$", f"{C.BOLD}{C.CYAN}# \\2{C.R}", text, flags=re.MULTILINE)
    return re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", f"{C.CYAN}\\1{C.R} {C.GRAY}(\\2){C.R}", text)


def is_markdown(text: str) -> bool:
    """Check if text contains markdown patterns."""
    markdown_patterns = [
        r"^#{1,6}\s+",
        r"\*\*.*?\*\*",
        r"`[^`]+`",
        r"\[.*?\]\(.*?\)",
    ]
    return any(re.search(pattern, text, re.MULTILINE) for pattern in markdown_patterns)
