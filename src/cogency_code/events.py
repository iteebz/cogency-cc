"""Event rendering logic for cogency-code.

Transforms cogency events to Textual renderables using cogency's formatting.
"""

from typing import Any

from rich.text import Text


def render_event(event: dict[str, Any]) -> Text | None:
    """Transform cogency event to Textual renderable.

    Uses cogency's existing format/parse tooling. Zero duplication.

    Args:
        event: Cogency event from the agent stream

    Returns:
        Rich Text object or None (for metrics handled elsewhere)
    """
    match event["type"]:
        case "user":
            if event["content"]:
                return Text(f"$ {event['content']}", style="bold cyan")
            return None

        case "think":
            if event["content"]:
                return Text(f"~ {event['content']}", style="dim italic")
            return None

        case "respond":
            if event["content"]:
                return Text(f"> {event['content']}", style="bold white")
            return None

        case "call":
            payload = event.get("payload", {})
            outcome = payload.get("outcome", "Tool execution")
            return Text(f"○ {outcome}", style="cyan")

        case "result":
            try:
                import json

                if event["content"]:
                    result_data = json.loads(event["content"])
                    outcome = result_data.get("outcome", "Tool completed")
                else:
                    outcome = event.get("payload", {}).get("outcome", "Tool completed")

                return Text(f"● {outcome}", style="green")
            except Exception:
                return Text("● Tool completed", style="green")

        case "metrics":
            return None

        case "execute":
            return None

        case "end":
            return Text("─ Session ended", style="yellow")

        case "error":
            payload = event.get("payload", {})
            error_msg = payload.get("error", event.get("content", "Unknown error"))
            return Text(f"✗ Error: {error_msg}", style="red")

        case "interrupt":
            return Text("⚠ Interrupted", style="yellow")

        case "cancelled":
            return Text("⚠ Cancelled", style="yellow")

        case _:
            fallback = event.get("content") or event.get("payload", {}).get("outcome")
            if not fallback:
                fallback = "Unknown event"
            return Text(f"? {fallback}", style="red")
