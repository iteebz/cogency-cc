"""Entry point for cogency-cc CLI application."""

import asyncio
import datetime
import shutil
import sys
import uuid

from .agent import create_agent
from .context import show_context
from .conversations import get_last_conversation
from .instructions import find_project_root
from .renderer import Renderer
from .state import Config
from .storage_ext import StorageExt
from .sessions import SessionManager, handle_session_cli_commands

session_manager_ext = StorageExt()
session_manager = SessionManager(session_manager_ext)


def _print_session_details(session: dict):
    created_at = datetime.datetime.fromtimestamp(session["created_at"])
    model_info = f"{session['model_config'].get('provider', 'N/A')}/{session['model_config'].get('model', 'N/A')}"
    print(f"  Tag: {session['tag']}")
    print(f"  Conversation ID: {session['conversation_id']}")
    print(f"  Model: {model_info}")
    print(f"  Created At: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("----------------------------------------")


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
    config.load()

    # Model alias flags should be processed after loading config to override it
    for flag, values in model_alias_flags.items():
        if flag in sys.argv:
            sys.argv.remove(flag)
            config.provider = values.get("provider")
            config.model = values.get("model")
            break
    config.save()  # Persist any changes

    config, resuming = asyncio.run(handle_session_cli_commands(sys.argv, config, session_manager))

    if "--set" in sys.argv:
        idx = sys.argv.index("--set")
        if idx + 1 < len(sys.argv):
            set_arg = sys.argv[idx + 1]
            if set_arg == "model":
                if idx + 2 < len(sys.argv):
                    model_name = sys.argv[idx + 2]
                    sys.argv.pop(idx)
                    sys.argv.pop(idx)
                    sys.argv.pop(idx)

                    found_model = False
                    for flag, values in model_alias_flags.items():
                        # Remove leading -- from flag for comparison
                        if flag[2:] == model_name:
                            config.provider = values.get("provider")
                            config.model = values.get("model")
                            print(f"Model set to: {config.provider}/{config.model}")
                            found_model = True
                            break

                    if not found_model:
                        print(f"Error: Unknown model alias '{model_name}'.", file=sys.stderr)
                        print("Available model aliases:", file=sys.stderr)
                        for flag in model_alias_flags:
                            print(f"  - {flag[2:]}", file=sys.stderr)
                        sys.exit(1)
                else:
                    print("Error: --set model requires a model name.", file=sys.stderr)
                    sys.exit(1)
            else:
                print(
                    f"Error: Unknown --set argument: {set_arg}. Only 'model' is supported.",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print("Error: --set requires an argument (e.g., model).", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)  # Exit after setting the model

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
        await asyncio.wait_for(renderer.render_stream(stream), timeout=60.0)
    except asyncio.TimeoutError:
        print("\nAgent execution timed out after 60 seconds.")
        return
    finally:
        if stream and hasattr(stream, "aclose"):
            await stream.aclose()
        if hasattr(agent, "config") and hasattr(agent.config, "llm"):
            llm = agent.config.llm
            if llm and hasattr(llm, "close"):
                await llm.close()


if __name__ == "__main__":
    main()
