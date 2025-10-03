"""Entry point for cogency-code TUI application."""

import argparse
import sys

from .app import CogencyCode


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="cogency-code - TUI agent built by cogency, for cogency"
    )
    
    # Check if this is a resume command
    if len(sys.argv) > 1 and sys.argv[1] == "resume":
        parser.add_argument("resume", help="Resume from an existing conversation")
        return parser.parse_args()
    
    # Add query argument (doesn't start with -)
    parser.add_argument("query", nargs="*", help="Single request query (bypasses TUI)")
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Handle emergency single-request mode
    if args.query:
        # Single request mode
        from .agent import create_agent
        from .state import Config
        
        config = Config(
            provider="glm",
            user_id="cogency"
        )
        
        agent = create_agent(config)
        query = " ".join(args.query)  # Join all query args as the query
        
        print(f"> {query}")
        print("-" * 50)
        
        import asyncio
        async def run_query():
            from cogency.cli.display import Renderer
            renderer = Renderer()
            
            # The agent itself is an async generator - pass it directly
            await renderer.render_stream(agent(query=query, user_id="cogency", conversation_id=None))
        
        asyncio.run(run_query())
        print("\n" + "-" * 50)
        return

    if hasattr(args, 'resume'):
        # Launch resume selection UI
        app = CogencyCode(
            llm_provider="glm",
            mode="resume_selection"
        )
    else:
        # Normal launch
        app = CogencyCode(
            llm_provider="glm"
        )

    try:
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
