"""Configuration state management."""

import dataclasses
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cogency.lib.llms.rotation import get_api_key as rotated_api_key
from cogency.lib.llms.rotation import load_keys as rotated_keys
from cogency.lib.uuid7 import uuid7


def _default_config_dir() -> Path:
    """Select config directory based on environment."""
    override = os.getenv("COGENCY_CONFIG_DIR")
    if override:
        return Path(override) / ".cogency"

    if os.getenv("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / f"cogency-cc-tests-{os.getpid()}"

    # Check for a project-local .cogency directory
    project_local_config_dir = Path.cwd() / ".cogency"
    if project_local_config_dir.is_dir():
        return project_local_config_dir

    return Path.home() / ".cogency"


@dataclass
class Config:
    """Runtime configuration persisted to ~/.cogency/cc.json."""

    provider: str = "glm"
    model: str | None = None
    user_id: str = "cc_user"
    conversation_id: str = field(default_factory=uuid7)
    api_keys: dict[str, str] = field(default_factory=dict)
    debug_mode: bool = False

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
        if not self.config_file.exists():
            return

        with open(self.config_file, encoding="utf-8") as f:
            data = json.load(f)
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def save(self) -> None:
        """Save configuration to file."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        data = {
            "provider": self.provider,
            "model": self.model,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "api_keys": self.api_keys,
            "debug_mode": self.debug_mode,
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
        return {
            "provider": self.provider,
            "model": self.model,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "api_keys": self.api_keys,
            "debug_mode": self.debug_mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        valid_keys = {f.name for f in dataclasses.fields(cls) if f.init}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)

    @classmethod
    def load_or_default(cls, **kwargs) -> "Config":
        config = cls(**kwargs)
        config.load()
        return config
