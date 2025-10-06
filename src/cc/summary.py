"""Summary inspection for conversations."""

from cogency.lib.storage import SQLite

from .conversations import get_last_conversation
from .instructions import find_project_root
from .lib.color import C


async def show_summary():
    root = find_project_root()
    if not root:
        print("No project root found")
        return

    conv_id = get_last_conversation(str(root))
    if not conv_id:
        print("No conversation found")
        return

    storage = SQLite()
    summaries = await storage.load_summaries(conv_id)

    if not summaries:
        print("No summaries yet")
        return

    print(f"{C.gray}conversation: {conv_id[:8]}{C.R}")
    print(f"{C.gray}summaries: {len(summaries)}{C.R}\n")

    for i, s in enumerate(summaries):
        print(f"{C.gray}[{i}] {s['count']} msgs{C.R}")
        print(f"{s['summary']}\n")
