"""Entry point for cogency-cc CLI application."""

import asyncio
import sys
import uuid

from .agent import create_agent
from .conversations import get_last_conversation
from .context import show_context
from .instructions import find_project_root
from .renderer import Renderer
from .state import Config


def main() -> None:
    provider = None
    conv_id = None
    force_new = False
    interactive = False

    if "--debug" in sys.argv:
        sys.argv.remove("--debug")
        from cogency.lib.logger import set_debug

        set_debug(True)

    provider_flags = {
        "--openai": "openai",
        "--gemini": "gemini",
        "--claude": "anthropic",
        "--glm": "glm",
    }
    for flag, p_name in provider_flags.items():
        if flag in sys.argv:
            sys.argv.remove(flag)
            provider = p_name
            break

    if "--new" in sys.argv:
        sys.argv.remove("--new")
        force_new = True

    if "--interactive" in sys.argv or "-i" in sys.argv:
        if "--interactive" in sys.argv:
            sys.argv.remove("--interactive")
        if "-i" in sys.argv:
            sys.argv.remove("-i")
        interactive = True

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
        idx = sys.argv.index("--nuke")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1] == "profile":
            from .profile import nuke_profile
            asyncio.run(nuke_profile())
        sys.exit(0)

    config = Config(user_id="cogency")
    if provider:
        config.provider = provider

    resuming = False
    if not conv_id and not force_new:
        root = find_project_root()
        if root:
            conv_id = get_last_conversation(str(root))
            if conv_id:
                resuming = True

    if not conv_id:
        conv_id = str(uuid.uuid4())

    if interactive:
        asyncio.run(run_interactive(config, conv_id))
    else:
        if len(sys.argv) <= 1:
            print("Usage: cc <query> [--glm|--claude|--gemini|--openai] [--new] [-i|--interactive]")
            sys.exit(1)

        query = " ".join(sys.argv[1:])
        cli_instruction = ""

        agent = create_agent(config, cli_instruction)
        asyncio.run(run_one_shot(agent, query, conv_id, resuming))


async def run_one_shot(agent, query: str, conv_id: str, resuming: bool = False):
    from cogency.lib.storage import SQLite

    storage = SQLite()
    msgs = await storage.load_messages(conv_id, "cogency")
    summaries = []

    if resuming:
        pass

    llm = agent.config.llm if hasattr(agent, "config") else None
    renderer = Renderer(messages=msgs, llm=llm, conv_id=conv_id, summaries=summaries)
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


async def run_interactive(config: Config, conv_id: str):
    agent = create_agent(config)
    renderer = Renderer()

    print(f"cc interactive mode | {config.provider} | {conv_id[:8]}")
    print("Type 'exit' or Ctrl+D to quit\n")

    try:
        while True:
            try:
                query = input("$ ")
                if not query.strip():
                    continue
                if query.lower() in ("exit", "quit"):
                    break

                stream = agent(query=query, user_id="cogency", conversation_id=conv_id, chunks=True)
                await renderer.render_stream(stream)
                print()

            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n^C")
                continue

    finally:
        if hasattr(agent, "config") and hasattr(agent.config, "llm"):
            llm = agent.config.llm
            if llm and hasattr(llm, "close"):
                await llm.close()


if __name__ == "__main__":
    main()
