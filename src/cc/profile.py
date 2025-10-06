"""Profile inspection and management."""

import json

from cogency.lib.storage import DB, SQLite

from .lib.color import C
from .state import Config


async def show_profile():
    config = Config()
    storage = SQLite()

    user_id = config.user_id
    profile = await storage.load_profile(user_id)

    if not profile:
        print(f"No profile for {user_id}")
        return

    history = _get_profile_history(user_id)

    print(f"{C.gray}user: {user_id}{C.R}")
    print(f"{C.gray}evolutions: {len(history)}{C.R}")
    print(f"{C.gray}total chars: {sum(h['chars'] for h in history)}{C.R}\n")

    print(f"{C.cyan}latest profile:{C.R}")
    print(json.dumps(profile, indent=2))
    print()

    if len(history) > 1:
        print(f"{C.gray}evolution history:{C.R}")
        for h in history[-5:]:
            print(f"  v{h['version']}: {h['chars']} chars")


async def nuke_profile():
    config = Config()
    storage = SQLite()

    user_id = config.user_id
    deleted = await storage.delete_profile(user_id)

    if deleted > 0:
        print(f"{C.green}✓{C.R} Deleted {deleted} profile versions for {user_id}")
    else:
        print(f"No profile found for {user_id}")


def _get_profile_history(user_id: str) -> list[dict]:
    db_path = ".cogency/store.db"
    with DB.connect(db_path) as db:
        rows = db.execute(
            "SELECT version, char_count, created_at FROM profiles WHERE user_id = ? ORDER BY version",
            (user_id,),
        ).fetchall()
        return [{"version": r[0], "chars": r[1], "created_at": r[2]} for r in rows]
