"""Pure formatting functions - no state, no side effects."""

import re


def tool_name(name: str) -> str:
    """Extract short name from dotted tool name."""
    return name.split(".")[-1] if "." in name else name


def tool_arg(args: dict) -> str:
    """Extract primary arg for display."""
    if not isinstance(args, dict):
        return ""

    for k in ["file", "path", "pattern", "query", "command", "url"]:
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

    # "+N lines" for read/grep
    if m := re.match(r"(Grep|Wrote|Read) .+ \((\d+) lines?\)", outcome):
        return f"+{m.group(2)} lines"

    # "+N/-M" for edits
    if m := re.match(r"(Edited|Modified) .+ \(([-+0-9/]+)\)", outcome):
        return m.group(2)

    # "N items" for ls
    if m := re.match(r"Listed (\d+) items", outcome):
        return f"{m.group(1)} items"

    # "N matches" for grep
    if m := re.match(r"Found (\d+) (matches|results)", outcome):
        return f"{m.group(1)} {m.group(2)}"

    return outcome


def format_call(call) -> str:
    """Format tool call for display."""
    name = tool_name(call.name)
    arg = tool_arg(call.args)
    return f"{name}({arg}): ..." if arg else f"{name}(): ..."


def format_result(call, payload) -> str:
    """Format tool result for display."""
    name = tool_name(call.name)
    arg = tool_arg(call.args)
    outcome = tool_outcome(payload)
    base = f"{name}({arg})" if arg else f"{name}()"
    return f"{base}: {outcome}"
