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
                return Text(f"$ {event['content']}\n", style="bold cyan")
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
            try:
                from cogency.tools.format import format_call_human
                from cogency.tools.parse import parse_tool_call

                call = parse_tool_call(event["content"])
                action = format_call_human(call)
                return Text(f"\n○ {action}", style="cyan")
            except Exception:
                return Text("\n○ Tool execution", style="cyan")

        case "result":
            payload = event.get("payload", {})
            outcome = payload.get("outcome", "Tool completed")
            content = payload.get("content", "")
            error = payload.get("error", False)
            
            style = "red" if error else "green"
            result_text = Text(f"● {outcome}", style=style)
            
            if content:
                result_text.append(f"\n{content}", style="dim")
            
            return result_text

        case "metrics":
            return None

        case "end":
            return Text("\n─ Session ended\n", style="yellow")

        case _:
            return Text(f"? {event.get('content', 'Unknown event')}", style="red")
