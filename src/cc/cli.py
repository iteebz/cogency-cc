import asyncio
import sys
import uuid
from typing import Annotated

import typer

from .agent import create_agent
from .alias import MODEL_ALIASES
from .commands import context_command, nuke_command, profile_command
from .conversations import get_last_conversation
from .lib.fs import root
from .renderer import Renderer
from .session import session_app
from .state import Config
from .storage import Snapshots


async def run_agent(
    agent,
    query: str,
    conv_id: str,
    resuming: bool = False,
    evo_mode: bool = False,
    config=None,
):
    from cogency.lib.storage import SQLite

    storage = SQLite()
    msgs = await storage.load_messages(conv_id, "cogency")
    summaries = []

    if resuming:
        pass

    llm = agent.config.llm if hasattr(agent, "config") else None
    renderer = Renderer(
        messages=msgs,
        llm=llm,
        conv_id=conv_id,
        summaries=summaries,
        config=config,
        evo_mode=evo_mode,
        enable_rolling_summary=config.enable_rolling_summary,
        rolling_summary_threshold=config.rolling_summary_threshold,
    )
    stream = agent(query=query, user_id="cogency", conversation_id=conv_id, chunks=True)
    try:
        await asyncio.wait_for(renderer.render_stream(stream), timeout=60.0)
    except asyncio.TimeoutError:
        typer.echo("\nAgent execution timed out after 60 seconds.")
        return
    finally:
        if stream and hasattr(stream, "aclose"):
            await stream.aclose()
        if hasattr(agent, "config") and hasattr(agent.config, "llm"):
            llm = agent.config.llm
            if llm and hasattr(llm, "close"):
                await llm.close()


app = typer.Typer(
    help="Cogency Code CLI for interacting with AI agents.",
    invoke_without_command=True,
    pretty_exceptions_enable=False,
)


@app.callback()
def main(
    ctx: typer.Context,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            "-d",
            help="Enable debug logging.",
        ),
    ] = False,
) -> None:
    if debug:
        from cogency.lib.logger import set_debug

        set_debug(True)

    config = Config(user_id="cogency")
    config.load()
    ctx.obj = {"config": config, "snapshots": Snapshots()}


@app.command("run")
def run_cmd(
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
):
    """Run a query with the agent."""
    config: Config = ctx.obj["config"]

    if model_alias:
        values = MODEL_ALIASES[model_alias]
        config.provider = values.get("provider")
        config.model = values.get("model")
    config.save()

    query = " ".join(query_parts)
    if not query:
        typer.echo(ctx.parent.get_help())
        sys.exit(0)

    # Resolve conversation ID
    resuming_or_forking = False
    current_conv_id = conversation_id_arg
    resuming = False

    if not current_conv_id and not new and not resuming_or_forking:
        project_root = root()
        if project_root:
            last_conv_id = get_last_conversation(str(project_root))
            if last_conv_id:
                current_conv_id = last_conv_id
                resuming = True

    if not current_conv_id:
        current_conv_id = str(uuid.uuid4())

    agent = create_agent(config, "")
    typer.echo(f"Using model: {config.model or config.provider}")
    asyncio.run(run_agent(agent, query, current_conv_id, resuming, evo, config))


app.add_typer(session_app, name="session")
app.command("nuke")(nuke_command)
app.command("profile")(profile_command)
app.command("context")(context_command)

if __name__ == "__main__":
    app()
