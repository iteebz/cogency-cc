"""Entry point for cogency-code TUI application."""

import argparse
import sys

from .app import CogencyCode


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="cogency-code - TUI agent built by cogency, for cogency"
    )
    parser.add_argument(
        "--provider",
        choices=["glm", "anthropic", "openai", "gemini"],
        default="glm",
        help="LLM provider to use (default: glm)",
    )
    parser.add_argument("--session", default="dev_work", help="Conversation ID (default: dev_work)")
    parser.add_argument("--user", default="cogency_user", help="User ID (default: cogency_user)")
    parser.add_argument(
        "--mode",
        choices=["auto", "resume", "replay"],
        default="auto",
        help="Agent mode (default: auto)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    app = CogencyCode(
        llm_provider=args.provider, conversation_id=args.session, user_id=args.user, mode=args.mode
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
