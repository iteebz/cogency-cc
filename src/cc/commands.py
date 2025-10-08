import asyncio
import shutil

import typer

from .context import show_context
from .lib.fs import root
from .profile import show_profile
from .state import Config
from .storage import Snapshots


def nuke_command(
    ctx: typer.Context,
) -> None:
    """Deletes the .cogency directory in the project root."""
    project_root = root()
    if project_root:
        cogency_path = project_root / ".cogency"
        if cogency_path.exists() and cogency_path.is_dir():
            typer.echo(f"Nuking {cogency_path}...")
            shutil.rmtree(cogency_path)
            typer.echo("Done.")
        else:
            typer.echo(f"No .cogency directory found at {cogency_path}.")
    else:
        typer.echo("No project root found.")


def profile_command(
    ctx: typer.Context,
) -> None:
    """Shows the user profile."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(show_profile(config, snapshots))


def context_command(
    ctx: typer.Context,
) -> None:
    """Shows the assembled context."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(show_context(config, snapshots))
