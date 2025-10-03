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
        conversation_id=app.conversation_id,
        user_id=app.user_id,
        exclude=["metrics", "chunk"]
    )
    
    if not messages:
        return {
            "type": "respond",
            "content": "No conversation to compact.",
            "payload": {},
            "timestamp": 0,
        }
    
    history = [{"role": "user" if msg["type"] == "user" else "assistant", "content": msg["content"]} for msg in messages]
    
    compress_prompt = [{"role": "user", "content": COMPACT_PROMPT}]
    
    summary = await app.agent.llm.generate(history + compress_prompt)
    
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
