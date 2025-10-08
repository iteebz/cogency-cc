"""Configuration state management."""

import dataclasses
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cogency.lib.rotation import get_api_key as rotated_api_key
from cogency.lib.rotation import load_keys as rotated_keys


def _default_config_dir() -> Path:
    """Select config directory based on environment."""
    override = os.getenv("COGENCY_CONFIG_DIR")
    if override:
        return Path(override) / ".cogency"

    if os.getenv("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / f"cogency-cc-tests-{os.getpid()}"

    return Path.home() / ".cogency"


@dataclass
class Config:
    """Runtime configuration persisted to ~/.cogency/cc.json."""

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
    enable_rolling_summary: bool = True
    rolling_summary_threshold: int = 10

    config_dir: Path = field(default_factory=lambda: _default_config_dir())
    config_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.config_file = self.config_dir / "cc.json"

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
            except (OSError, json.JSONDecodeError) as e:
                print(
                    f"Warning: Could not load config from {self.config_file}. Error: {e}. Using default settings.",
                    file=sys.stderr,
                )

    def save(self) -> None:
        """Save configuration to file."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(mode=0o700)

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

    def to_dict(self) -> dict:
        """Return a dictionary representation of the config for serialization."""
        return {
            "provider": self.provider,
            "model": self.model,
            "mode": self.mode,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "tools": self.tools,
            "identity": self.identity,
            "token_limit": self.token_limit,
            "compact_threshold": self.compact_threshold,
            "enable_rolling_summary": self.enable_rolling_summary,
            "rolling_summary_threshold": self.rolling_summary_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Construct a Config object from a dictionary."""
        # Filter out keys that are not part of the Config constructor
        # This handles cases where the stored dict might have extra keys
        valid_keys = {f.name for f in dataclasses.fields(cls) if f.init}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
