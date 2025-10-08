import asyncio
import datetime

import click
from cogency.lib.ids import uuid7

from .state import Config
from .storage import Snapshots


@click.group(name="session")
@click.pass_context
def session_cli(ctx: click.Context):
    """Manage saved agent sessions."""
    pass


async def _save_session(ctx: click.Context, tag: str):
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]

    result_tag_or_id = await snapshots.save_session(
        tag, config.conversation_id, config.user_id, config.to_dict()
    )
    if result_tag_or_id == tag:
        click.echo(f"Session '{tag}' overwritten.")
    else:
        click.echo(f"Session saved with tag: {tag}")


@session_cli.command(name="save")
@click.argument("tag")
@click.pass_context
def save_session_command(ctx: click.Context, tag: str):
    """Save the current conversation as a session with a given TAG."""
    asyncio.run(_save_session(ctx, tag))


async def _list_sessions(ctx: click.Context):
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]

    sessions = await snapshots.list_sessions(config.user_id)
    if sessions:
        click.echo("Saved Sessions:")
        click.echo(f"{'TAG':<15} {'CONVERSATION_ID':<38} {'MODEL':<20} {'CREATED_AT':<20}")
        click.echo("-" * 95)
        for session in sessions:
            created_at = datetime.datetime.fromtimestamp(session["created_at"])
            model_info = f"{session['model_config'].get('provider', 'N/A')}/{session['model_config'].get('model', 'N/A')}"
            click.echo(
                f"{session['tag']:15} {session['conversation_id']:38} {model_info:20} {created_at.strftime('%Y-%m-%d %H:%M:%S'):20}"
            )
    else:
        click.echo("No sessions saved.")


@session_cli.command(name="list")
@click.pass_context
def list_sessions_command(ctx: click.Context):
    """List all saved sessions."""
    asyncio.run(_list_sessions(ctx))


async def _resume_session(ctx: click.Context, tag: str):
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]

    loaded_session = await snapshots.load_session(tag, config.user_id)
    if loaded_session:
        config.conversation_id = loaded_session["conversation_id"]
        _apply_config_from_loaded_session(config, loaded_session)
        click.echo(f"Resumed session '{tag}'.")
        ctx.obj["resuming_or_forking"] = True
    else:
        raise click.ClickException(f"Session with tag '{tag}' not found.")


@session_cli.command(name="resume")
@click.argument("tag")
@click.pass_context
def resume_session_command(ctx: click.Context, tag: str):
    """Resume a saved session by TAG."""
    asyncio.run(_resume_session(ctx, tag))


async def _fork_session(ctx: click.Context, tag: str):
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]

    loaded_session = await snapshots.load_session(tag, config.user_id)
    if loaded_session:
        new_conversation_id = uuid7()
        config.conversation_id = new_conversation_id
        _apply_config_from_loaded_session(config, loaded_session)
        click.echo(f"Forked session '{tag}' into new conversation: {new_conversation_id}")
        ctx.obj["resuming_or_forking"] = True
    else:
        raise click.ClickException(f"Session with tag '{tag}' not found.")


@session_cli.command(name="fork")
@click.argument("tag")
@click.pass_context
def fork_session_command(ctx: click.Context, tag: str):
    """Fork a saved session by TAG into a new conversation."""
    asyncio.run(_fork_session(ctx, tag))


async def _delete_session(ctx: click.Context, tag: str):
    config: Config = ctx.obj["config"]
    snapshots: Snapshots = ctx.obj["snapshots"]

    deleted_count = await snapshots.delete_session(tag, config.user_id)
    if deleted_count > 0:
        click.echo(f"Session '{tag}' deleted.")
    else:
        click.echo(f"Session '{tag}' not found for user '{config.user_id}'.")


@session_cli.command(name="delete")
@click.argument("tag")
@click.pass_context
def delete_session_command(ctx: click.Context, tag: str):
    """Delete a saved session by TAG."""
    asyncio.run(_delete_session(ctx, tag))


def _apply_config_from_loaded_session(config: Config, loaded_session: dict):
    """Applies configuration from a loaded session to the current config object."""
    model_config = loaded_session.pop("model_config", None)
    config.update(**loaded_session)

    if model_config:
        config.provider = model_config.get("provider", config.provider)
        config.model = model_config.get("model", config.model)
