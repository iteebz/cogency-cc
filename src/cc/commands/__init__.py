import asyncio
import shutil

import typer

from ..config import Config
from ..lib.fs import root
from ..lib.sqlite import Snapshots
from .context import show_context
from .export import export_conversation
from .profile import show_profile
from .session import session_app


def nuke_command(ctx: typer.Context) -> None:
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


def profile_command(ctx: typer.Context) -> None:
    """Shows the user profile."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(show_profile(config, snapshots))


def context_command(ctx: typer.Context) -> None:
    """Shows the assembled context."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(show_context(config, snapshots))


def export_command(
    ctx: typer.Context,
    conversation_id: str = typer.Option(
        None, "--conv", "-c", help="Conversation ID to export (uses last if not specified)"
    ),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown/json)"),
    output: str = typer.Option(
        None, "--output", "-o", help="Output file path (prints to stdout if not specified)"
    ),
    no_color: bool = typer.Option(False, "--no-color", help="Strip ANSI color codes"),
) -> None:
    """Export a conversation to markdown or JSON format."""
    config: Config = ctx.obj["config"]
    asyncio.run(export_conversation(config, conversation_id, format, output, no_color))


__all__ = [
    "show_context",
    "show_profile",
    "session_app",
    "nuke_command",
    "profile_command",
    "context_command",
    "export_command",
]
