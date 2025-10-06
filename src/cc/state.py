"""Configuration state management."""

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cogency.lib.rotation import get_api_key as rotated_api_key
from cogency.lib.rotation import load_keys as rotated_keys


def _default_config_dir() -> Path:
    """Select config directory based on environment."""
    override = os.getenv("COGENCY_CODE_CONFIG_DIR")
    if override:
        return Path(override)

    if os.getenv("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / f"cogency-cc-tests-{os.getpid()}"

    return Path.home() / ".cogency-cc"


@dataclass
class Config:
    """Runtime configuration persisted to ~/.cogency-cc/config.json."""

    provider: str = "glm"
    model: str | None = None
    mode: str = "resume"
    user_id: str = "new_user"
    conversation_id: str = "dev_work"
    tools: list[str] = field(default_factory=lambda: ["file", "web", "memory"])
    api_keys: dict[str, str] = field(default_factory=dict)
    identity: str = field(default_factory=lambda: "code")
    token_limit: int = 100000
    compact_threshold: int = 12000

    config_dir: Path = field(default_factory=lambda: _default_config_dir())
    config_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.config_file = self.config_dir / "config.json"
        self.load()

    def get_api_key(self, provider: str) -> str | None:
        """Get API key: environment variables override stored keys."""
        rotated = rotated_api_key(provider)
        if rotated:
            return rotated

        return self.api_keys.get(provider)

    def get_api_key_status(self, provider: str) -> str:
        """Get display status for API key."""
        if rotated_keys(provider.upper()):
            return f"✓ {provider.title()} (env)"
        if self.api_keys.get(provider):
            return f"✓ {provider.title()} (saved)"
        return f"✗ {provider.title()}"

    def load(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
            except Exception:
                pass  # Start with defaults if config is broken

    def save(self) -> None:
        """Save configuration to file."""
        self.config_dir.mkdir(exist_ok=True, mode=0o700)

        data = {
            "provider": self.provider,
            "model": self.model,
            "mode": self.mode,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "tools": self.tools,
            "api_keys": self.api_keys,
            "identity": self.identity,
            "token_limit": self.token_limit,
            "compact_threshold": self.compact_threshold,
        }

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def update(self, **kwargs) -> None:
        """Update config values and save."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()


def list_conversations() -> list[dict]:
    """List all conversations with metadata."""
    from cogency.lib.storage import DB

    with DB.connect() as db:
        rows = db.execute("""
            SELECT
                conversation_id,
                user_id,
                MIN(timestamp) as first_message,
                MAX(timestamp) as last_message,
                COUNT(*) as message_count
            FROM messages
            GROUP BY conversation_id, user_id
            ORDER BY last_message DESC
        """).fetchall()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "first": row[2],
                "last": row[3],
                "count": row[4],
            }
            for row in rows
        ]
