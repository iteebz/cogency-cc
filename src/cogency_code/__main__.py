"""Entry point for cogency-code CLI application."""

import asyncio
import sys
import uuid

from cogency.cli.display import Renderer

from .agent import create_agent
from .conversations import get_last_conversation
from .instructions import find_project_root
from .state import Config


def main() -> None:
    provider = None
    conv_id = None
    force_new = False
    chunks = False
    interactive = False

    if "--openai" in sys.argv:
        sys.argv.remove("--openai")
        provider = "openai"
    elif "--gemini" in sys.argv:
        sys.argv.remove("--gemini")
        provider = "gemini"
    elif "--claude" in sys.argv:
        sys.argv.remove("--claude")
        provider = "anthropic"
    elif "--glm" in sys.argv:
        sys.argv.remove("--glm")
        provider = "glm"

    if "--new" in sys.argv:
        sys.argv.remove("--new")
        force_new = True

    if "--chunks" in sys.argv:
        sys.argv.remove("--chunks")
        chunks = True

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
        asyncio.run(run_interactive(config, conv_id, chunks))
    else:
        if len(sys.argv) <= 1:
            print("Usage: cc <query> [--glm|--claude|--gemini|--openai] [--chunks] [--new] [-i|--interactive]")
            sys.exit(1)

        query = " ".join(sys.argv[1:])
        cli_instruction = (
            ""
            if resuming
            else (
                "CLI ONE-SHOT MODE\n"
                "- Treat the next user message as the full task; there will be no follow-up prompts.\n"
                "- Answer in your first §respond message with only the information the user requested.\n"
                "- Do not introduce yourself, list capabilities, or ask questions.\n"
                "- Immediately emit §end after delivering the answer.\n"
                "- Example: user says 'what is 2+2' → respond '4' then §end."
            )
        )

        agent = create_agent(config, cli_instruction)
        asyncio.run(run_one_shot(agent, query, conv_id, chunks))


async def run_one_shot(agent, query: str, conv_id: str, chunks: bool):
    renderer = Renderer()
    stream = agent(query=query, user_id="cogency", conversation_id=conv_id, chunks=chunks)
    try:
        await renderer.render_stream(stream)
    finally:
        if hasattr(agent, "config") and hasattr(agent.config, "llm"):
            llm = agent.config.llm
            if llm and hasattr(llm, "close"):
                await llm.close()


async def run_interactive(config: Config, conv_id: str, chunks: bool):
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

                stream = agent(query=query, user_id="cogency", conversation_id=conv_id, chunks=chunks)
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
