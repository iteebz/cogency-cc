"""Event rendering logic for cogency-code."""

import json
from typing import Any

from rich.text import Text

from cogency.core.exceptions import ProtocolError
from cogency.tools.parse import parse_tool_call


def render_event(event: dict[str, Any]) -> Text | None:
    """Transform cogency event to Textual renderable."""
    event_type = event.get("type")

    if event_type in ("metrics", "execute"):
        return None

    if event_type == "user":
        content = event.get("content")
        return Text(f"$ {content}", style="bold cyan") if content else None

    if event_type == "think":
        content = event.get("content")
        return Text(f"~ {content}", style="dim italic") if content else None

    if event_type == "respond":
        content = event.get("content")
        return Text(f"> {content}", style="bold white") if content else None

    if event_type == "call":
        call = _parse_call(event)
        if call:
            name = call["name"].replace("_", " ").title()
            arg = _primary_arg(call["args"])
            if arg:
                return Text(f"○ {name} · {arg}", style="cyan")
            return Text(f"○ {name}", style="cyan")

        outcome = event.get("payload", {}).get("outcome", "Tool execution")
        return Text(f"○ {outcome}", style="cyan")

    if event_type == "result":
        payload = event.get("payload", {})
        outcome = payload.get("outcome") or _extract_outcome(event) or "Tool completed"
        return Text(f"● {outcome}", style="green")

    if event_type == "end":
        return Text("─ Session ended", style="yellow")

    if event_type == "error":
        payload = event.get("payload", {})
        error = payload.get("error", event.get("content", "Unknown error"))
        return Text(f"✗ Error: {error}", style="red")

    if event_type in ("interrupt", "cancelled"):
        label = "Interrupted" if event_type == "interrupt" else "Cancelled"
        return Text(f"⚠ {label}", style="yellow")

    fallback = event.get("content") or event.get("payload", {}).get("outcome", "Unknown event")
    return Text(f"? {fallback}", style="red")


def _parse_call(event: dict[str, Any]) -> dict[str, Any] | None:
    """Parse tool call from event content."""
    content = event.get("content")
    if not content:
        return None

    try:
        call = parse_tool_call(content)
        return {"name": call.name, "args": call.args or {}}
    except (ProtocolError, json.JSONDecodeError, KeyError, TypeError):
        return None


def _primary_arg(args: dict[str, Any]) -> str | None:
    """Extract most relevant arg for display."""
    if not args:
        return None

    for key in ("file", "pattern", "query", "command"):
        if key in args and args[key]:
            return str(args[key])

    return None


def _extract_outcome(event: dict[str, Any]) -> str | None:
    """Extract outcome from JSON content."""
    content = event.get("content")
    if not content:
        return None

    try:
        data = json.loads(content)
        return data.get("outcome") if isinstance(data, dict) else None
    except (TypeError, json.JSONDecodeError):
        return None
