import asyncio
import contextlib
import os
import uuid
from pathlib import Path
from typing import Annotated

import click
import typer

from .agent import create_agent
from .alias import MODEL_ALIASES
from .commands import context_command, nuke_command, profile_command, session_app
from .config import Config
from .conversations import get_last_conversation
from .lib.fs import root
from .lib.sqlite import Snapshots
from .render import Renderer


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


def apply_model_alias(config: Config, model_alias: str | None) -> None:
    """Apply a model alias to the config if provided."""
    if not model_alias:
        return

    if model_alias not in MODEL_ALIASES:
        typer.echo(f"Unknown model alias: {model_alias}")
        raise typer.Exit(code=1)

    values = MODEL_ALIASES[model_alias]
    config.provider = values.get("provider", config.provider)
    config.model = values.get("model")


async def run_agent(
    agent,
    query: str,
    conv_id: str,
    resuming: bool = False,
    evo_mode: bool = False,
    config=None,
):
    from .lib.sqlite import storage as get_storage

    storage = get_storage(config)
    msgs = await storage.load_messages(conv_id, config.user_id)
    latest_metric = await storage.load_latest_metric(conv_id)

    renderer = Renderer(
        messages=msgs,
        llm=agent.config.llm,
        conv_id=conv_id,
        config=config,
        evo_mode=evo_mode,
        latest_metric=latest_metric,
    )

    model_str = getattr(agent.config.llm, "http_model", "") or ""
    is_codex = "codex" in model_str.lower()
    stream = agent(
        query=query,
        user_id=config.user_id,
        conversation_id=conv_id,
        chunks=not is_codex,
        generate=is_codex,
    )
    try:
        await renderer.render_stream(stream)
    finally:
        if stream and hasattr(stream, "aclose"):
            await stream.aclose()
        if agent.config.llm and hasattr(agent.config.llm, "close"):
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
    new: Annotated[
        bool,
        typer.Option(
            "--new",
            "-n",
            help="Start a new conversation, ignoring history.",
            rich_help_panel="Run Options",
        ),
    ] = False,
    evo: Annotated[
        bool,
        typer.Option(
            "--evo",
            "-e",
            help="Enable evolutionary mode (experimental).",
            rich_help_panel="Run Options",
        ),
    ] = False,
    conversation_id_arg: Annotated[
        str | None,
        typer.Option(
            "--conv",
            "-c",
            help="Specify a conversation ID to resume or start.",
            rich_help_panel="Run Options",
        ),
    ] = None,
    model_alias: Annotated[
        str | None,
        typer.Option(
            "--model-alias",
            "-m",
            help="Use a predefined model alias.",
            rich_help_panel="Run Options",
        ),
    ] = None,
) -> None:
    config = Config.load_or_default()
    if debug is not None:
        config.debug_mode = debug
    if config.debug_mode:
        from cogency.lib.logger import set_debug

        set_debug(True)
    apply_model_alias(config, model_alias)

    import sqlite3

    try:
        snapshots = Snapshots()
    except (PermissionError, sqlite3.OperationalError):
        typer.echo("Error: Cannot create or open database in the current directory.")
        typer.echo("Please run from a directory where you have write permissions.")
        raise typer.Exit(code=1) from None

    ctx.obj = {"config": config, "snapshots": snapshots}
    ctx.obj["root_flags"] = {
        "new": new,
        "evo": evo,
        "conversation_id": conversation_id_arg,
        "model_alias": model_alias,
    }

    if ctx.invoked_subcommand is None and not ctx.args:  # no query provided, show help as usual
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
    new: Annotated[
        bool,
        typer.Option(
            "--new",
            "-n",
            help="Start a new conversation, ignoring history.",
        ),
    ] = False,
    evo: Annotated[
        bool,
        typer.Option(
            "--evo",
            "-e",
            help="Enable evolutionary mode (experimental).",
        ),
    ] = False,
    conversation_id_arg: Annotated[
        str | None,
        typer.Option(
            "--conv",
            "-c",
            help="Specify a conversation ID to resume or start.",
        ),
    ] = None,
    model_alias: Annotated[
        str | None,
        typer.Option(
            "--model-alias",
            "-m",
            help="Use a predefined model alias.",
            rich_help_panel="Model Configuration",
        ),
    ] = None,
    save_config: Annotated[
        bool,
        typer.Option(hidden=True),
    ] = True,
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
        evo = evo or root_flags.get("evo", False)
        conversation_id_arg = conversation_id_arg or root_flags.get("conversation_id")
        model_alias = model_alias or root_flags.get("model_alias")

        apply_model_alias(config, model_alias)
        if save_config:
            config.save()
        query = " ".join(query_parts)
        if not query:
            parent = ctx.parent or ctx
            typer.echo(parent.get_help())
            raise typer.Exit()
        current_conv_id = _resolve_conversation_id(new, conversation_id_arg)
        if new:
            typer.echo(f"Starting new conversation with ID: {current_conv_id}")

        config.conversation_id = current_conv_id

        resuming = (not new) and (current_conv_id != str(uuid.uuid4()))

        agent = create_agent(config, "")
        asyncio.run(run_agent(agent, query, current_conv_id, resuming, evo, config))
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


app.command(name="profile")(profile_command)
app.command(name="nuke")(nuke_command)
app.command(name="context")(context_command)
app.add_typer(session_app)
