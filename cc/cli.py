import asyncio
import contextlib
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Annotated

import click
import typer

from .agent import create_agent
from .commands import export_command, nuke_command, session_app
from .config import Config
from .render import render
from .storage import Snapshots, get_last_conversation, root

_NEW_OPTION = Annotated[
    bool,
    typer.Option(
        "--new",
        "-n",
        help="Start a new conversation, ignoring history.",
        rich_help_panel="Run Options",
    ),
]

_CONV_OPTION = Annotated[
    str | None,
    typer.Option(
        "--conv",
        "-c",
        help="Specify a conversation ID to resume or start.",
        rich_help_panel="Run Options",
    ),
]


class DefaultRunGroup(typer.core.TyperGroup):
    """Group that falls back to a default command when none is provided."""

    def __init__(self, *args, **kwargs):
        self._default_command: str | None = kwargs.pop("default_command", None)
        super().__init__(*args, **kwargs)

    def resolve_command(self, ctx: click.Context, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if self._default_command:
                default_cmd = self.get_command(ctx, self._default_command)
                if default_cmd is None:
                    raise
                return self._default_command, default_cmd, args
            raise


class RunGroup(DefaultRunGroup):
    """Default group for cc CLI that falls back to the default handler."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, default_command="__default__", **kwargs)


async def run_agent(agent, query: str, conv_id: str, user_id: str):
    stream = agent(query=query, user_id=user_id, conversation_id=conv_id)
    try:
        await render(stream)
    finally:
        if hasattr(stream, "aclose"):
            await stream.aclose()
        if hasattr(agent.config.llm, "close"):
            await agent.config.llm.close()


app = typer.Typer(
    help="Cogency Code CLI for interacting with AI agents.",
    invoke_without_command=True,
    pretty_exceptions_enable=False,
    cls=RunGroup,
    rich_markup_mode="rich",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


@app.callback()
def main(
    ctx: typer.Context,
    debug: Annotated[
        bool | None,
        typer.Option(
            "--debug/--no-debug",
            "-d/-D",
            help="Enable or disable debug logging for this run.",
        ),
    ] = None,
    new: _NEW_OPTION = False,
    conversation_id_arg: _CONV_OPTION = None,
) -> None:
    config = Config.load_or_default()
    if debug is not None:
        config.debug_mode = debug
    if config.debug_mode:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    try:
        snapshots = Snapshots()
    except (PermissionError, sqlite3.OperationalError):
        typer.echo("Error: Cannot create or open database in the current directory.")
        typer.echo("Please run from a directory where you have write permissions.")
        raise typer.Exit(code=1) from None

    ctx.obj = {"config": config, "snapshots": snapshots}
    ctx.obj["root_flags"] = {
        "new": new,
        "conversation_id": conversation_id_arg,
    }

    if ctx.invoked_subcommand is None and not ctx.args:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=2)


def _resolve_conversation_id(new: bool, conversation_id_arg: str | None) -> str:
    if new:
        return str(uuid.uuid4())
    if conversation_id_arg:
        return conversation_id_arg

    project_root = root()
    conv_id = None
    if project_root:
        conv_id = get_last_conversation(str(project_root))

    if not conv_id:
        conv_id = get_last_conversation()

    if not conv_id:
        conv_id = str(uuid.uuid4())

    return conv_id


@app.command("__default__", hidden=True)
def default_cmd(
    ctx: typer.Context,
    query_parts: Annotated[
        list[str],
        typer.Argument(help="The query to run with the agent."),
    ],
    new: _NEW_OPTION = False,
    conversation_id_arg: _CONV_OPTION = None,
):
    """Run a query with the agent."""
    config: Config = ctx.obj["config"]
    previous_cwd: Path | None = None
    project_root = root()

    if project_root:
        current_cwd = Path.cwd()
        if current_cwd != project_root:
            try:
                os.chdir(project_root)
                previous_cwd = current_cwd
            except OSError as e:
                typer.echo(f"Failed to switch to project root {project_root}: {e}")
                raise typer.Exit(code=1) from e

    try:
        root_flags = ctx.obj.get("root_flags", {})
        new = new or root_flags.get("new", False)
        conversation_id_arg = conversation_id_arg or root_flags.get("conversation_id")

        query = " ".join(query_parts)
        if not query:
            parent = ctx.parent or ctx
            typer.echo(parent.get_help())
            raise typer.Exit()
        current_conv_id = _resolve_conversation_id(new, conversation_id_arg)
        if new:
            typer.echo(f"Starting new conversation with ID: {current_conv_id}")

        config.conversation_id = current_conv_id
        agent = create_agent(config, "")
        asyncio.run(run_agent(agent, query, current_conv_id, config.user_id))
    finally:
        if previous_cwd and Path.cwd() != previous_cwd:
            with contextlib.suppress(OSError):
                os.chdir(previous_cwd)


@app.command()
def set(
    ctx: typer.Context,
    provider: Annotated[
        str,
        typer.Argument(help="The LLM provider to use (e.g., 'openai', 'gemini', 'glm')."),
    ],
    model: Annotated[
        str | None,
        typer.Argument(help="The specific model to use (e.g., 'gpt-4', 'gemini-pro')."),
    ] = None,
):
    """Set the default LLM provider and model in the local configuration."""
    config: Config = ctx.obj["config"]
    config.provider = provider
    config.model = model
    config.save()
    typer.echo(
        f"Configuration updated: provider='{config.provider}', model='{config.model or 'default'}'"
    )


app.command(name="nuke")(nuke_command)
app.command(name="export")(export_command)
app.add_typer(session_app)
