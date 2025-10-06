"""Manual context compaction."""

import json
import time
import uuid

from cogency.lib.logger import logger
from cogency.lib.storage import SQLite

from .agent import create_agent
from .conversations import get_last_conversation
from .instructions import find_project_root
from .lib.color import C
from .state import Config
from .storage import SummaryStorage

CULL_PROMPT = """Context too large. Summarize and cull.

Messages:
{messages}

Return JSON:
{{"summary": "2 sentence summary", "keep_system": true, "cull_before_timestamp": <timestamp>}}

Keep system prompt. Cull everything before timestamp. Be aggressive."""


def _get_tokens(msgs: list[dict]) -> int:
    for m in reversed(msgs):
        if m.get("type") == "metric" and "total" in m:
            return m["total"].get("input", 0) + m["total"].get("output", 0)
    return sum(len(m.get("content", "")) // 4 for m in msgs)


async def maybe_cull(
    conversation_id: str,
    user_id: str,
    msg_storage,
    sum_storage: SummaryStorage,
    llm,
    threshold: int,
) -> bool:
    msgs = await msg_storage.load_messages(conversation_id, None)

    if _get_tokens(msgs) < threshold:
        return False

    formatted = "\n".join(
        [f"[{m.get('timestamp', 0)}] {m['type']}: {m['content'][:150]}" for m in msgs]
    )
    prompt = CULL_PROMPT.format(messages=formatted)

    result = await llm.generate([{"role": "user", "content": prompt}])
    if not result:
        return False

    clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(clean)
        summary = data.get("summary", "")
        cull_ts = data.get("cull_before_timestamp", 0)
        keep_system = data.get("keep_system", True)

        if not summary or not cull_ts:
            return False

        culled = await sum_storage.cull_messages(conversation_id, cull_ts, keep_system)

        if culled > 0:
            start_ts = msgs[0].get("timestamp", time.time())
            await sum_storage.save_summary(
                conversation_id, user_id, summary, culled, start_ts, cull_ts
            )
            logger.debug(f"🗑️  CULLED: {culled} msgs, kept summary")
            return True

    except json.JSONDecodeError as e:
        logger.debug(f"Cull JSON error: {e}")

    return False


async def compact_context():
    root = find_project_root()
    if not root:
        print("No project root found")
        return

    conv_id = get_last_conversation(str(root))
    if not conv_id:
        print("No conversation found")
        return

    config = Config()
    msg_storage = SQLite()
    sum_storage = SummaryStorage()

    msgs = await msg_storage.load_messages(conv_id, "cogency")
    tokens = _get_tokens(msgs)

    print(f"{C.gray}conversation: {conv_id[:8]}{C.R}")
    print(f"{C.gray}messages: {len(msgs)}{C.R}")
    print(f"{C.gray}tokens: {tokens:,}{C.R}\n")

    if tokens < config.compact_threshold:
        print(
            f"{C.gray}Context under threshold ({config.compact_threshold:,} tokens), no compaction needed{C.R}"
        )
        return

    print(f"{C.yellow}Compacting context...{C.R}")

    agent = create_agent(config)
    llm = agent.config.llm if hasattr(agent, "config") else None

    if not llm:
        print(f"{C.red}No LLM configured{C.R}")
        return

    culled = await maybe_cull(
        conv_id, "cogency", msg_storage, sum_storage, llm, config.compact_threshold
    )

    if culled:
        new_id = str(uuid.uuid4())
        config.update(conversation_id=new_id)

        msgs_after = await msg_storage.load_messages(conv_id, "cogency")
        tokens_after = _get_tokens(msgs_after)

        print(f"{C.green}✓ Compacted context{C.R}")
        print(f"{C.gray}messages: {len(msgs)} → {len(msgs_after)}{C.R}")
        print(f"{C.gray}tokens: {tokens:,} → {tokens_after:,}{C.R}")
        print(f"{C.cyan}new conversation: {new_id[:8]}{C.R}\n")

        print(f"{C.gray}kept messages:{C.R}")
        for m in msgs_after:
            t = m.get("type", "unknown")
            preview = m.get("content", "")[:60]
            if len(m.get("content", "")) > 60:
                preview += "..."
            print(f"  {t}: {preview}")
    else:
        print(f"{C.gray}No compaction performed{C.R}")

    if hasattr(llm, "close"):
        await llm.close()
