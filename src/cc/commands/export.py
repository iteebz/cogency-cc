"""Export conversations to various formats."""

import contextlib
import json
import re
from datetime import datetime
from io import StringIO
from pathlib import Path

from ..config import Config
from ..conversations import get_last_conversation
from ..lib.sqlite import storage as get_storage

__all__ = ["export_conversation"]


def _strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def _format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp as readable date."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def _count_turns(messages: list[dict]) -> int:
    """Count user query turns in conversation."""
    return sum(1 for msg in messages if msg.get("type") == "user")


async def render_messages_to_string(
    messages: list[dict], config: Config, no_color: bool = False
) -> str:
    """Render messages through the renderer to a string."""
    from ..render import Renderer

    # Capture output to string
    output = StringIO()

    # Create renderer without history printing
    renderer = Renderer(messages=[], config=config)

    # Manually replay events and capture output
    from contextlib import redirect_stdout

    # Create async generator from messages
    async def message_stream():
        for msg in messages:
            yield msg

    # Render to string buffer
    with redirect_stdout(output):
        with contextlib.suppress(Exception):
            # If rendering fails, fall back to simple text
            await renderer.render_stream(message_stream())

    result = output.getvalue()

    if no_color:
        result = _strip_ansi_codes(result)

    return result


async def export_conversation(
    config: Config,
    conversation_id: str | None = None,
    format: str = "markdown",
    output: str | None = None,
    no_color: bool = False,
) -> None:
    """Export a conversation to markdown or JSON format.

    Args:
        config: Application configuration
        conversation_id: ID of conversation to export (uses last if None)
        format: Output format ('markdown' or 'json')
        output: Optional file path to write (prints to stdout if None)
        no_color: Strip ANSI color codes from output
    """
    # Resolve conversation ID
    if conversation_id is None:
        conversation_id = get_last_conversation()
        if conversation_id is None:
            print("No conversations found.")
            return

    # Load messages from storage
    storage = get_storage(config)
    messages = await storage.load_messages(conversation_id, config.user_id)

    if not messages:
        print("No messages found in conversation.")
        return

    # Export based on format
    if format == "json":
        content = json.dumps(messages, indent=2)
    else:
        # Render as markdown with metadata header
        rendered = await render_messages_to_string(messages, config, no_color=no_color)

        # Extract metadata from first message
        first_msg = messages[0]
        timestamp = first_msg.get("timestamp", 0)
        formatted_date = _format_timestamp(timestamp) if timestamp else "Unknown"
        turn_count = _count_turns(messages)

        content = f"""# Conversation Export

- **ID**: {conversation_id}
- **Date**: {formatted_date}
- **Timestamp**: {timestamp}
- **Turns**: {turn_count}
- **Messages**: {len(messages)}

---

{rendered}
"""

    # Output to file or stdout
    if output:
        output_path = Path(output)
        output_path.write_text(content)
        print(f"Exported to {output}")
    else:
        print(content)
