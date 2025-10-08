"Entry point for cogency-cc CLI application."

import asyncio
import sys
import uuid

import click

from .agent import create_agent
from .alias import MODEL_ALIASES
from .commands import context, nuke, profile
from .conversations import get_last_conversation
from .lib.fs import root
from .renderer import Renderer
from .session import session_cli
from .state import Config


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
        click.echo("\nAgent execution timed out after 60 seconds.")
        return
    finally:
        if stream and hasattr(stream, "aclose"):
            await stream.aclose()
        if hasattr(agent, "config") and hasattr(agent.config, "llm"):
            llm = agent.config.llm
            if llm and hasattr(llm, "close"):
                await llm.close()


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, debug: bool) -> None:
    """Cogency Code CLI for interacting with AI agents."""
    ctx.ensure_object(dict)

    if debug:
        from cogency.lib.logger import set_debug

        set_debug(True)

    config = Config(user_id="cogency")
    config.load()
    ctx.obj["config"] = config

    from .storage import Snapshots

    ctx.obj["snapshots"] = Snapshots()

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


@main.command("run")
@click.option("--new", is_flag=True, help="Start a new conversation, ignoring history.")
@click.option("--evo", is_flag=True, help="Enable evolutionary mode (experimental).")
@click.option("--conv", "conversation_id_arg", help="Specify a conversation ID to resume or start.")
@click.option(
    "--model-alias",
    type=click.Choice(list(MODEL_ALIASES.keys())),
    help="Use a predefined model alias.",
)
@click.argument("query_parts", nargs=-1)
@click.pass_context
def run_cmd(
    ctx: click.Context,
    new: bool,
    evo: bool,
    conversation_id_arg: str | None,
    model_alias: str | None,
    query_parts: tuple[str, ...],
):
    """Run a query with the agent."""
    config = ctx.obj["config"]

    if model_alias:
        values = MODEL_ALIASES[model_alias]
        config.provider = values.get("provider")
        config.model = values.get("model")
    config.save()

    query = " ".join(query_parts)
    if not query:
        click.echo(ctx.parent.get_help())
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
    click.echo(f"Using model: {config.model or config.provider}")
    asyncio.run(run_agent(agent, query, current_conv_id, resuming, evo, config))


# Add other commands
main.add_command(nuke)
main.add_command(profile)
main.add_command(context)
main.add_command(session_cli)

if __name__ == "__main__":
    main()
