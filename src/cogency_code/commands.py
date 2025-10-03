"""Slash command handlers for cogency-code."""

import uuid


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
    return {
        "type": "respond",
        "content": "/compact not yet implemented",
        "payload": {},
        "timestamp": 0,
    }


COMMANDS = {
    "clear": handle_clear,
    "compact": handle_compact,
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
