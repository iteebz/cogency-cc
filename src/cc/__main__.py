"""Entry point for cogency-cc CLI application."""

import asyncio
import shutil
import sys
import uuid

from .agent import create_agent
from .context import show_context
from .conversations import get_last_conversation
from .instructions import find_project_root
from .renderer import Renderer
from .state import Config


def nuke_cogency_dir() -> None:
    root = find_project_root()
    if root:
        cogency_path = root / ".cogency"
        if cogency_path.exists() and cogency_path.is_dir():
            print(f"Nuking {cogency_path}...")
            shutil.rmtree(cogency_path)
            print("Done.")
        else:
            print(f"No .cogency directory found at {cogency_path}.")
    else:
        print("No project root found.")
    sys.exit(0)


def main() -> None:
    conv_id = None
    force_new = False
    evo_mode = False

    if "--debug" in sys.argv:
        sys.argv.remove("--debug")
        from cogency.lib.logger import set_debug

        set_debug(True)

    model_alias_flags = {
        "--codex": {"provider": "openai", "model": "gpt-5-codex-low"},
        "--gemini": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "--claude": {"provider": "anthropic"},
        "--glm": {"provider": "glm"},
        "--gpt41": {"provider": "openai", "model": "gpt-4.1"},
    }

    config = Config(user_id="cogency")

    for flag, values in model_alias_flags.items():
        if flag in sys.argv:
            sys.argv.remove(flag)
            config.provider = values.get("provider")
            config.model = values.get("model")
            break

    if "--new" in sys.argv:
        sys.argv.remove("--new")
        force_new = True

    if "--evo" in sys.argv:
        sys.argv.remove("--evo")
        evo_mode = True

    if "--conv" in sys.argv:
        idx = sys.argv.index("--conv")
        if idx + 1 < len(sys.argv):
            conv_id = sys.argv[idx + 1]
            sys.argv.pop(idx)
            sys.argv.pop(idx)

    if "--profile" in sys.argv:
        import json
        from pathlib import Path

        profile_path = Path.cwd() / ".cogency" / "profile.json"
        if not profile_path.exists():
            print("No profile found")
            sys.exit(0)

        with open(profile_path) as f:
            profile = json.load(f)
            print(json.dumps(profile, indent=2))
        sys.exit(0)

    if "--context" in sys.argv:
        asyncio.run(show_context())
        sys.exit(0)

    if "--summary" in sys.argv:
        from .summary import show_summary

        asyncio.run(show_summary())
        sys.exit(0)

    if "--profile" in sys.argv:
        from .profile import show_profile

        asyncio.run(show_profile())
        sys.exit(0)

    if "--nuke" in sys.argv:
        nuke_cogency_dir()
        sys.exit(0)

    if "--compact" in sys.argv:
        from .compact import compact_context

        asyncio.run(compact_context())
        sys.exit(0)

    resuming = False
    if not conv_id and not force_new:
        root = find_project_root()
        if root:
            conv_id = get_last_conversation(str(root))
            if conv_id:
                resuming = True

    if not conv_id:
        conv_id = str(uuid.uuid4())

    if len(sys.argv) <= 1:
        print("Usage: cc <query> [--glm|--claude|--gemini|--codex] [--new]")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    cli_instruction = ""

    agent = create_agent(config, cli_instruction)

    print(f"Using model: {config.model or config.provider}")

    asyncio.run(run(agent, query, conv_id, resuming, evo_mode, config))


async def run(
    agent, query: str, conv_id: str, resuming: bool = False, evo_mode: bool = False, config=None
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
    )
    stream = agent(query=query, user_id="cogency", conversation_id=conv_id, chunks=True)
    try:
        await renderer.render_stream(stream)
    finally:
        if stream and hasattr(stream, "aclose"):
            await stream.aclose()
        if hasattr(agent, "config") and hasattr(agent.config, "llm"):
            llm = agent.config.llm
            if llm and hasattr(llm, "close"):
                await llm.close()


if __name__ == "__main__":
    main()
