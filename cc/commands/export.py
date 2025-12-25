"""Export conversations to various formats."""

import json
import re
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..storage import get_last_conversation
from ..storage import storage as get_storage

__all__ = ["export_conversation"]


def _strip_ansi(text: str) -> str:
    return re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])").sub("", text)


def _format_messages(messages: list[dict], no_color: bool = False) -> str:
    lines = []
    for msg in messages:
        t = msg.get("type", "")
        content = msg.get("content", "")
        if t == "user":
            lines.append(f"$ {content}")
        elif t == "respond":
            lines.append(content)
        elif t == "think":
            lines.append(f"[think] {content}")
        elif t == "call":
            lines.append(f"[call] {content}")
        elif t == "result":
            payload = msg.get("payload", {})
            outcome = payload.get("outcome") or payload.get("message") or "ok"
            lines.append(f"[result] {outcome}")
    result = "\n".join(lines)
    return _strip_ansi(result) if no_color else result


async def export_conversation(
    config: Config,
    conversation_id: str | None = None,
    format: str = "markdown",
    output: str | None = None,
    no_color: bool = False,
) -> None:
    if conversation_id is None:
        conversation_id = get_last_conversation()
        if conversation_id is None:
            print("No conversations found.")
            return

    storage = get_storage(config)
    messages = await storage.load_messages(conversation_id, config.user_id)

    if not messages:
        print("No messages found in conversation.")
        return

    if format == "json":
        content = json.dumps(messages, indent=2)
    else:
        rendered = _format_messages(messages, no_color=no_color)
        first_msg = messages[0]
        timestamp = first_msg.get("timestamp", 0)
        formatted_date = (
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            if timestamp
            else "Unknown"
        )
        turn_count = sum(1 for msg in messages if msg.get("type") == "user")

        content = f"""# Conversation Export

- **ID**: {conversation_id}
- **Date**: {formatted_date}
- **Turns**: {turn_count}
- **Messages**: {len(messages)}

---

{rendered}
"""

    if output:
        Path(output).write_text(content)
        print(f"Exported to {output}")
    else:
        print(content)
