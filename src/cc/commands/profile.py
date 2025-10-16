"""Profile inspection and management."""

import json

import typer
from cogency.lib.sqlite import DB

from ..config import Config
from ..lib.sqlite import Snapshots
from ..render.color import C


async def show_profile(config: Config, snapshots: Snapshots):
    from ..lib.sqlite import storage as get_storage

    storage = get_storage(config)

    user_id = config.user_id
    profile = await storage.load_profile(user_id)

    if not profile:
        typer.echo(f"No profile for {user_id}")
        return

    history = _get_profile_history(user_id)

    typer.echo(f"{C.gray}user: {user_id}{C.R}")
    typer.echo(f"{C.gray}evolutions: {len(history)}{C.R}")
    typer.echo(f"{C.gray}total chars: {sum(h['chars'] for h in history)}{C.R}\n")

    typer.echo(f"{C.cyan}latest profile:{C.R}")
    typer.echo(json.dumps(profile, indent=2))
    typer.echo()

    if len(history) > 1:
        typer.echo(f"{C.gray}evolution history:{C.R}")
        for h in history[-5:]:
            typer.echo(f"  v{h['version']}: {h['chars']} chars")


async def nuke_profile(config: Config, snapshots: Snapshots):
    from ..lib.sqlite import storage as get_storage

    storage = get_storage(config)

    user_id = config.user_id
    deleted = await storage.delete_profile(user_id)

    if deleted > 0:
        typer.echo(f"{C.green}✓{C.R} Deleted {deleted} profile versions for {user_id}")
    else:
        typer.echo(f"No profile found for {user_id}")


def _get_profile_history(user_id: str) -> list[dict]:
    from ..config import _default_config_dir

    db_path = str(_default_config_dir() / "store.db")
    with DB.connect(db_path) as db:
        rows = db.execute(
            "SELECT version, char_count, created_at FROM profiles WHERE user_id = ? ORDER BY version",
            (user_id,),
        ).fetchall()
        return [{"version": r[0], "chars": r[1], "created_at": r[2]} for r in rows]
