import asyncio
import datetime
from typing import Annotated

import typer
from cogency.lib.uuid7 import uuid7

from ..config import Config
from ..lib.sqlite import Snapshots

session_app = typer.Typer(name="session", help="Manage saved agent sessions.")


async def _save_session(config: Config, snapshots: Snapshots, tag: str):
    await snapshots.save_session(tag, config.conversation_id, config.user_id, config.to_dict())
    typer.echo(f"Session saved with tag: {tag}")


@session_app.command(name="save")
def save_session_command(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="TAG to save the session with.")],
):
    """Save the current conversation as a session with a given TAG."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(_save_session(config, snapshots, tag))


async def _list_sessions(config: Config, snapshots: Snapshots):
    sessions = await snapshots.list_sessions(config.user_id)
    if sessions:
        typer.echo("Saved Sessions:")
        typer.echo(f"{'TAG':<15} {'CONVERSATION_ID':<38} {'MODEL':<20} {'CREATED_AT':<20}")
        typer.echo("-" * 95)
        for session in sessions:
            created_at = datetime.datetime.fromtimestamp(session["created_at"])
            model_info = f"{session['model_config'].get('provider', 'N/A')}/{session['model_config'].get('model', 'N/A')}"
            typer.echo(
                f"{session['tag']:15} {session['conversation_id']:38} {model_info:20} {created_at.strftime('%Y-%m-%d %H:%M:%S'):20}"
            )
    else:
        typer.echo("No sessions saved.")


@session_app.command(name="list")
def list_sessions_command(
    ctx: typer.Context,
):
    """List all saved sessions."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(_list_sessions(config, snapshots))


async def _resume_session(config: Config, snapshots: Snapshots, tag: str):
    loaded_session = await snapshots.load_session(tag, config.user_id)
    if loaded_session:
        config.conversation_id = loaded_session["conversation_id"]
        _apply_config_from_loaded_session(config, loaded_session)
        typer.echo(f"Resumed session '{tag}'.")
        # ctx.obj["resuming_or_forking"] = True # This needs to be handled in cli.py
    else:
        raise typer.BadParameter(f"Session with tag '{tag}' not found.")


@session_app.command(name="resume")
def resume_session_command(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="TAG of the session to resume.")],
):
    """Resume a saved session by TAG."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(_resume_session(config, snapshots, tag))


async def _fork_session(config: Config, snapshots: Snapshots, tag: str):
    loaded_session = await snapshots.load_session(tag, config.user_id)
    if loaded_session:
        new_conversation_id = uuid7()
        config.conversation_id = new_conversation_id
        _apply_config_from_loaded_session(config, loaded_session)
        typer.echo(f"Forked session '{tag}' into new conversation: {new_conversation_id}")
        # ctx.obj["resuming_or_forking"] = True # This needs to be handled in cli.py
    else:
        raise typer.BadParameter(f"Session with tag '{tag}' not found.")


@session_app.command(name="fork")
def fork_session_command(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="TAG of the session to fork.")],
):
    """Fork a saved session by TAG into a new conversation."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(_fork_session(config, snapshots, tag))


async def _delete_session(config: Config, snapshots: Snapshots, tag: str):
    deleted_count = await snapshots.delete_session(tag, config.user_id)
    if deleted_count > 0:
        typer.echo(f"Session '{tag}' deleted.")
    else:
        typer.echo(f"Session '{tag}' not found for user '{config.user_id}'.")


@session_app.command(name="delete")
def delete_session_command(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="TAG of the session to delete.")],
):
    """Delete a saved session by TAG."""
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]
    asyncio.run(_delete_session(config, snapshots, tag))


def _apply_config_from_loaded_session(config: Config, loaded_session: dict):
    """Applies configuration from a loaded session to the current config object."""
    model_config = loaded_session.pop("model_config", None)
    config.update(**loaded_session)

    if model_config:
        config.provider = model_config.get("provider", config.provider)
        config.model = model_config.get("model", config.model)
