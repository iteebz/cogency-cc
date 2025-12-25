import asyncio
import shutil
from pathlib import Path

import typer

from .export import export_conversation
from .session import session_app

HOME_DIR = Path.home() / ".cogency"


def nuke_command(ctx: typer.Context) -> None:
    """Deletes the ~/.cogency directory."""
    if HOME_DIR.exists() and HOME_DIR.is_dir():
        typer.echo(f"Nuking {HOME_DIR}...")
        shutil.rmtree(HOME_DIR)
        typer.echo("Done.")
    else:
        typer.echo(f"No .cogency directory found at {HOME_DIR}.")


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
    from ..config import Config

    config: Config = ctx.obj["config"]
    asyncio.run(export_conversation(config, conversation_id, format, output, no_color))


__all__ = ["session_app", "nuke_command", "export_command"]
