"""Context inspection for conversations."""

import json
from pathlib import Path

from cogency.lib.storage import SQLite

from .conversations import get_last_conversation
from .instructions import find_project_root
from .lib.color import C


async def show_context():
    root = find_project_root()
    if not root:
        print("No project root found")
        return

    conv_id = get_last_conversation(str(root))
    if not conv_id:
        print("No conversation found")
        return

    storage = SQLite()
    msgs = await storage.load_messages(conv_id, "cogency")

    if not msgs:
        print("No messages in conversation")
        return

    dist = {}
    for m in msgs:
        t = m.get("type", "unknown")
        dist[t] = dist.get(t, 0) + 1

    print(f"{C.gray}conversation: {conv_id[:8]}{C.R}")
    print(f"{C.gray}messages: {len(msgs)}{C.R}")
    print(f"{C.gray}distribution:{C.R}")
    for t, count in sorted(dist.items(), key=lambda x: -x[1]):
        pct = int(count / len(msgs) * 100)
        print(f"  {t}: {count} ({pct}%)")
    print()

    for i, msg in enumerate(msgs):
        msg_type = msg.get("type", "unknown")
        role = msg.get("role", "")
        content = msg.get("content", "")

        if msg_type == "user":
            print(f"{C.cyan}[{i}] user{C.R}")
            print(f"{content}\n")

        elif msg_type == "assistant":
            print(f"{C.magenta}[{i}] assistant{C.R}")
            print(f"{content}\n")

        elif msg_type == "system":
            print(f"{C.gray}[{i}] system{C.R}")
            preview = content[:100] + "..." if len(content) > 100 else content
            print(f"{preview}\n")

        elif msg_type == "call":
            print(f"{C.cyan}[{i}] call{C.R}")
            try:
                call_data = json.loads(content) if isinstance(content, str) else content
                print(f"{json.dumps(call_data, indent=2)}\n")
            except Exception:
                print(f"{content}\n")

        elif msg_type == "result":
            print(f"{C.green}[{i}] result{C.R}")
            payload = msg.get("payload", {})
            if payload:
                print(f"{json.dumps(payload, indent=2)}\n")
            else:
                print(f"{content}\n")

        elif msg_type == "summary":
            print(f"{C.gray}[{i}] summary{C.R}")
            summary_data = msg.get("summary", content)
            print(f"{summary_data}\n")

        elif msg_type == "metric":
            total_data = msg.get("total", {})
            window_data = msg.get("window", {})
            print(f"{C.gray}[{i}] metric{C.R}")
            if total_data:
                print(f"  total: {total_data.get('input', 0)}→{total_data.get('output', 0)} tok")
            if window_data:
                print(f"  window: {window_data.get('input', 0)}→{window_data.get('output', 0)} tok")
            print()
