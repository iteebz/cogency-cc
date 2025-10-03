"""Entry point for cogency-code TUI application."""

import argparse
import asyncio
import sys
import uuid

from .app import CogencyCode


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "resume":
        try:
            app = CogencyCode(llm_provider="glm", mode="resume_selection")
            app.run()
        except KeyboardInterrupt:
            sys.exit(0)
        return
    
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        from .agent import create_agent
        from .state import Config
        from cogency.lib.storage import default_storage
        
        query = " ".join(sys.argv[1:])
        config = Config(provider="glm", user_id="cogency")
        agent = create_agent(config)
        conv_id = str(uuid.uuid4())
        
        async def run_query():
            from cogency.cli.display import Renderer
            
            renderer = Renderer()
            stream = agent(query=query, user_id="cogency", conversation_id=conv_id)
            try:
                await renderer.render_stream(stream)
            finally:
                # Clean up LLM session
                if hasattr(agent, 'config') and hasattr(agent.config, 'llm'):
                    llm = agent.config.llm
                    if llm and hasattr(llm, 'close'):
                        await llm.close()
        
        asyncio.run(run_query())
        return
    
    try:
        app = CogencyCode(llm_provider="glm")
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
