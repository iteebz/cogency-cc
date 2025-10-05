"""Slash command handlers for cogency-code."""

import uuid

COMPACT_PROMPT = """Compress this conversation into essential context.

Preserve:
- Key decisions and their rationale
- Current state and active goals
- Important technical details

Omit:
- Procedural chatter
- Redundant explanations
- Resolved issues

Be ruthlessly concise."""


async def handle_clear(app) -> dict:
    """Clear stream and start new ephemeral session."""
    app.stream_view.clear()
    app.conversation_id = str(uuid.uuid4())
    app.header.update_info(
        model_name=app.llm_provider.upper(),
        session_id=app.conversation_id[:8] + "...",
        mode=app.mode,
    )
    return {
        "type": "respond",
        "content": "Cleared. New ephemeral session.",
        "payload": {},
        "timestamp": 0,
    }


async def handle_compact(app) -> dict:
    """Compact conversation history into new session with summary."""
    from cogency.lib.storage import SQLite

    storage = SQLite()

    messages = await storage.load_messages(
        conversation_id=app.conversation_id, user_id=app.user_id, exclude=["metrics", "chunk"]
    )

    if not messages:
        return {
            "type": "respond",
            "content": "No conversation to compact.",
            "payload": {},
            "timestamp": 0,
        }

    history = [
        {"role": "user" if msg["type"] == "user" else "assistant", "content": msg["content"]}
        for msg in messages
    ]

    compress_prompt = [{"role": "user", "content": COMPACT_PROMPT}]

    summary = await app.agent.config.llm.generate(history + compress_prompt)

    new_id = str(uuid.uuid4())
    await storage.save_message(
        conversation_id=new_id,
        user_id=app.user_id,
        type="respond",
        content=summary,
    )

    app.stream_view.clear()
    app.conversation_id = new_id
    app.header.update_info(
        model_name=app.llm_provider.upper(),
        session_id=new_id[:8] + "...",
        mode=app.mode,
    )

    return {
        "type": "respond",
        "content": f"[Compacted]\n\n{summary}",
        "payload": {},
        "timestamp": 0,
    }


async def handle_docs(app) -> dict:
    """Surface CLI diagnostics guidance without bloating the TUI."""
    message = (
        "Diagnostics live in the base CLI. Use commands like:\n"
        "  cogency context system   # Show active system prompt\n"
        "  cogency context <id>     # Inspect assembled conversation\n"
        "  cogency stats            # Storage metrics\n"
        "  cogency users            # Learned profiles\n"
        "  cogency nuke             # Reset .cogency state\n"
    )

    return {
        "type": "respond",
        "content": message,
        "payload": {},
        "timestamp": 0,
    }


async def handle_profile(app) -> dict:
    """Show learned user profile."""
    from cogency.context.profile import get

    profile = await get(app.user_id)
    
    if not profile:
        return {
            "type": "respond",
            "content": f"No profile learned yet for user '{app.user_id}'.\n\nProfiles are learned automatically every 5 messages.",
            "payload": {},
            "timestamp": 0,
        }
    
    import json
    meta = profile.pop("_meta", {})
    content = json.dumps(profile, indent=2)
    
    msg_count = meta.get("messages_processed", "unknown")
    return {
        "type": "respond",
        "content": f"Profile for '{app.user_id}' ({msg_count} messages):\n\n{content}",
        "payload": {},
        "timestamp": 0,
    }


COMMANDS = {
    "clear": handle_clear,
    "compact": handle_compact,
    "docs": handle_docs,
    "profile": handle_profile,
}


async def dispatch(command: str, app) -> dict | None:
    """Dispatch slash command to handler."""
    cmd = command.lower()
    handler = COMMANDS.get(cmd)

    if handler:
        return await handler(app)

    return {
        "type": "respond",
        "content": f"Unknown command: /{cmd}",
        "payload": {},
        "timestamp": 0,
    }
