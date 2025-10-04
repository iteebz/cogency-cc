"""Tests for configuration state management."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from cogency_code.state import Config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()

    assert config.provider == "glm"
    assert config.mode == "resume"
    assert config.user_id == "new_user"
    assert config.tools == ["file", "web", "memory"]
    assert config.api_keys == {}


def test_get_api_key_env_priority():
    """Test that environment variables take precedence over stored keys."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"

        # Create config with stored key
        config = Config()
        config.config_dir = Path(temp_dir)
        config.config_file = config_path
        config.api_keys = {"openai": "stored_key"}
        config.save()

        # Load with env var override
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env_key"}):
            config = Config()
            config.config_dir = Path(temp_dir)
            config.config_file = config_path
            config.load()

            # Env var should win
            assert config.get_api_key("openai") == "env_key"


def test_config_persistence():
    """Test configuration persistence to file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"

        config = Config()
        config.config_dir = Path(temp_dir)
        config.config_file = config_path
        config.update(provider="anthropic", mode="resume", user_id="test_user")

        assert config_path.exists()

        with open(config_path) as f:
            data = json.load(f)

        assert data["provider"] == "anthropic"
        assert data["mode"] == "resume"
        assert data["user_id"] == "test_user"


def test_load_existing_config():
    """Test loading existing configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"

        # Write config file
        test_config = {
            "provider": "gemini",
            "mode": "replay",
            "user_id": "loaded_user",
            "tools": ["file", "web"],
            "api_keys": {"glm": "test_key"},
        }

        with open(config_path, "w") as f:
            json.dump(test_config, f)

        # Load config
        config = Config()
        config.config_dir = Path(temp_dir)
        config.config_file = config_path
        config.load()

        assert config.provider == "gemini"
        assert config.mode == "replay"
        assert config.user_id == "loaded_user"
        assert config.tools == ["file", "web"]
        assert config.api_keys == {"glm": "test_key"}


def test_get_api_key_status():
    """Test API key status display."""
    config = Config()
    config.api_keys = {"glm": "stored_key"}

    with patch.dict(os.environ, {}, clear=True):
        # Clear env vars first, then add what we want
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env_key"}, clear=False):
            assert config.get_api_key_status("glm") == "✓ Glm (saved)"
            assert config.get_api_key_status("openai") == "✓ Openai (env)"
            assert config.get_api_key_status("anthropic") == "✗ Anthropic"


def test_config_update():
    """Test the update method."""
    config = Config()

    config.update(
        provider="gemini", mode="resume", user_id="new_user", api_keys={"openai": "new_key"}
    )

    assert config.provider == "gemini"
    assert config.mode == "resume"
    assert config.user_id == "new_user"
    assert config.api_keys == {"openai": "new_key"}


def test_broken_config_handling():
    """Test handling of broken config files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"

        # Write invalid JSON
        with open(config_path, "w") as f:
            f.write("invalid json content")

        # Create config with custom path to avoid loading default config
        config = object.__new__(Config)  # Skip __post_init__
        config.provider = "glm"
        config.mode = "auto"
        config.user_id = "cogency_user"
        config.conversation_id = "dev_work"
        config.tools = ["file", "web", "memory"]
        config.api_keys = {}
        config.config_dir = Path(temp_dir)
        config.config_file = config_path

        config.load()  # Should not crash

        # Should fall back to defaults (unchanged since load failed)
        assert config.provider == "glm"
        assert config.mode == "auto"
