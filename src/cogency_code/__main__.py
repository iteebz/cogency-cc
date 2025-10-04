"""Entry point for cogency-code TUI application."""

import asyncio
import sys
import uuid

from .app import CogencyCode


def main() -> None:
    """Main entry point."""
    provider = None

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

    if len(sys.argv) > 1 and sys.argv[1] == "resume":
        try:
            app = (
                CogencyCode(llm_provider=provider, mode="resume_selection")
                if provider
                else CogencyCode(mode="resume_selection")
            )
            app.run()
        except KeyboardInterrupt:
            sys.exit(0)
        return

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        from cogency.core.agent import Agent

        from .identities import CODING_IDENTITY
        from .state import Config

        query = " ".join(sys.argv[1:])
        config = Config(user_id="cogency")
        if provider:
            config.provider = provider

        cli_instruction = (
            "CLI ONE-SHOT MODE\n"
            "- Treat the next user message as the full task; there will be no follow-up prompts.\n"
            "- Answer in your first §respond message with only the information the user requested.\n"
            "- Do not introduce yourself, list capabilities, or ask questions.\n"
            "- Immediately emit §end after delivering the answer.\n"
            "- Example: user says 'what is 2+2' → respond '4' then §end."
        )
        agent = Agent(
            llm=config.provider, mode="auto", identity=CODING_IDENTITY, instructions=cli_instruction
        )
        conv_id = str(uuid.uuid4())

        async def run_query():
            from cogency.cli.display import Renderer

            renderer = Renderer()
            stream = agent(query=query, user_id="cogency", conversation_id=conv_id)
            try:
                await renderer.render_stream(stream)
            finally:
                # Clean up LLM session
                if hasattr(agent, "config") and hasattr(agent.config, "llm"):
                    llm = agent.config.llm
                    if llm and hasattr(llm, "close"):
                        await llm.close()

        asyncio.run(run_query())
        return

    try:
        app = CogencyCode(llm_provider=provider) if provider else CogencyCode()
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
