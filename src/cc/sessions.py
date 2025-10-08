import asyncio
import datetime
import sys
from typing import Any

from .state import Config
from .storage_ext import StorageExt


class SessionManager:
    def __init__(self, storage_ext: StorageExt):
        self.storage_ext = storage_ext

    async def save_session(self, tag: str, conversation_id: str, user_id: str, config_dict: dict) -> str:
        return await self.storage_ext.save_session(tag, conversation_id, user_id, config_dict)

    async def list_sessions(self, user_id: str) -> list[dict]:
        return await self.storage_ext.list_sessions(user_id)

    async def load_session(self, tag: str, user_id: str) -> dict | None:
        return await self.storage_ext.load_session(tag, user_id)


async def handle_session_cli_commands(args: list[str], config: Config, session_manager: SessionManager) -> tuple[Config, bool]:
    """
    Handles CLI commands related to session management (--save, --saves, --resume).

    Args:
        args: The list of command-line arguments (sys.argv).
        config: The current Config object.
        session_manager: An instance of SessionManager.

    Returns:
        A tuple containing:
            - The potentially updated Config object.
            - A boolean indicating if a session was resumed.
    """
    resuming = False

    if "--save" in args:
        idx = args.index("--save")
        if idx + 1 < len(args):
            tag = args[idx + 1]
            # Remove --save and its argument from args
            args.pop(idx)
            args.pop(idx)
            result_tag_or_id = await session_manager.save_session(
                tag, config.conversation_id, config.user_id, config.to_dict()
            )
            if result_tag_or_id == tag:
                print(f"Session '{tag}' overwritten.")
            else:
                print(f"Session saved with tag: {tag}")
            sys.exit(0)
        else:
            print("Error: --save requires a tag.", file=sys.stderr)
            sys.exit(1)

    if "--saves" in args:
        args.remove("--saves")
        sessions = await session_manager.list_sessions(config.user_id)
        if sessions:
            print("Saved Sessions:")
            print(f"{'TAG':<15} {'CONVERSATION_ID':<38} {'MODEL':<20} {'CREATED_AT':<20}")
            print("-" * 95)
            for session in sessions:
                created_at = datetime.datetime.fromtimestamp(session["created_at"])
                model_info = f"{session['model_config'].get('provider', 'N/A')}/{session['model_config'].get('model', 'N/A')}"
                print(
                    f"{session['tag']:15} {session['conversation_id']:38} {model_info:20} {created_at.strftime('%Y-%m-%d %H:%M:%S'):20}"
                )
        else:
            print("No sessions saved.")
        sys.exit(0)

    if "--resume" in args:
        idx = args.index("--resume")
        if idx + 1 < len(args):
            tag = args[idx + 1]
            # Remove --resume and its argument from args
            args.pop(idx)
            args.pop(idx)
            loaded_session = await session_manager.load_session(tag, config.user_id)
            if loaded_session:
                config.conversation_id = loaded_session["conversation_id"]
                # Reconstruct config using from_dict
                loaded_config_dict = loaded_session["model_config"]
                loaded_config = Config.from_dict(loaded_config_dict)
                config.provider = loaded_config.provider
                config.model = loaded_config.model
                config.mode = loaded_config.mode
                config.user_id = loaded_config.user_id
                config.tools = loaded_config.tools
                config.identity = loaded_config.identity
                config.token_limit = loaded_config.token_limit
                config.compact_threshold = loaded_config.compact_threshold
                config.enable_rolling_summary = loaded_config.enable_rolling_summary
                config.rolling_summary_threshold = loaded_config.rolling_summary_threshold

                print(f"Resuming session with tag: {tag}")
                resuming = True
            else:
                print(f"Error: Session with tag '{tag}' not found.", file=sys.stderr)
                sys.exit(1)
        else:
            print("Error: --resume requires a tag.", file=sys.stderr)
            sys.exit(1)
            
    return config, resuming
