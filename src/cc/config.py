"""Configuration state management."""

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cogency.lib.llms.rotation import get_api_key as rotated_api_key
from cogency.lib.uuid7 import uuid7


def _load_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    env_vars = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_vars[key.strip()] = value.strip().strip("'\"")
    return env_vars


def _default_config_dir() -> Path:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / f"cogency-cc-tests-{os.getpid()}"
    local = Path.cwd() / ".cogency"
    return local if local.is_dir() else Path.home() / ".cogency"


@dataclass
class Config:
    provider: str = "glm"
    model: str | None = None
    user_id: str = "cc_user"
    conversation_id: str = field(default_factory=uuid7)
    api_keys: dict[str, str] = field(default_factory=dict)
    debug_mode: bool = False
    config_dir: Path = field(default_factory=_default_config_dir)
    config_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.config_file = self.config_dir / "cc.json"
        for key, value in _load_env_file(self.config_dir / ".env").items():
            if key not in os.environ:
                os.environ[key] = value

    def get_api_key(self, provider: str) -> str | None:
        return rotated_api_key(provider) or self.api_keys.get(provider)

    def load(self) -> None:
        if not self.config_file.exists():
            return
        with open(self.config_file, encoding="utf-8") as f:
            for key, value in json.load(f).items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def save(self) -> None:
        if not self.config_dir.exists():
            self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def update(self, **kwargs) -> None:
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
    def load_or_default(cls, **kwargs) -> "Config":
        config = cls(**kwargs)
        config.load()
        return config
