"""Tests for configuration state management."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from cc.state import Config


def test_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.provider == "glm"
    assert config.user_id == "new_user"
    assert config.tools == ["file", "web", "memory"]
    assert config.api_keys == {}


def test_api_key_env_priority():
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


def test_persistence():
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


def test_load_existing():
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


def test_api_key_status():
    """Test API key status display."""
    config = Config()
    config.api_keys = {"glm": "stored_key"}

    with patch.dict(os.environ, {}, clear=True):
        # Clear env vars first, then add what we want
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env_key"}, clear=False):
            assert config.get_api_key_status("glm") == "✓ Glm (saved)"
            assert config.get_api_key_status("openai") == "✓ Openai (env)"
            assert config.get_api_key_status("anthropic") == "✗ Anthropic"


def test_update():
    """Test the update method."""
    config = Config()

    config.update(
        provider="gemini", mode="resume", user_id="new_user", api_keys={"openai": "new_key"}
    )

    assert config.provider == "gemini"
    assert config.mode == "resume"
    assert config.user_id == "new_user"
    assert config.api_keys == {"openai": "new_key"}


def test_broken_config():
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


def test_default_identity():
    """Test config has default identity."""
    config = Config()
    assert config.identity == "code"


def test_identity_persistence(tmp_path):
    """Test identity persists to config file."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / "config.json"

        config = Config()
        config.config_dir = Path(temp_dir)
        config.config_file = config_file
        config.identity = "cothinker"
        config.save()

        # Load and verify
        with open(config_file) as f:
            data = json.load(f)

        assert data["identity"] == "cothinker"


def test_api_key_priority():
    """Test API key resolution priority: env > stored."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        config_dir = Path(temp_dir)

        # Create config with stored key
        test_config = {"provider": "glm", "api_keys": {"glm": "stored_key"}}

        with open(config_path, "w") as f:
            json.dump(test_config, f)

        # Load config with env var override
        with patch.dict(os.environ, {"GLM_API_KEY": "env_key"}, clear=True):
            config = Config()
            config.config_dir = config_dir
            config.config_file = config_path
            config.load()

            assert config.get_api_key("glm") == "env_key"


def test_default_values():
    """Test that defaults are sensible and minimal."""
    # Create fresh config without loading from disk
    config = object.__new__(Config)  # Skip __post_init__ to avoid loading
    config.provider = "glm"
    config.mode = "auto"
    config.user_id = "cogency"
    config.conversation_id = "dev_work"
    config.tools = ["file", "web", "memory"]
    config.api_keys = {}

    # Verify defaults align with cogency-cc design
    assert config.provider == "glm"  # Default GLM provider
    assert config.mode == "auto"  # Auto mode for compatibility
    assert config.user_id == "cogency"
    assert set(config.tools) == {"file", "web", "memory"}  # Standard tool set


def test_to_dict():
    """Test Config.to_dict() method."""
    with patch.object(Config, "load", lambda self: None):
        config = Config(
            provider="test_provider",
            model="test_model",
            mode="test_mode",
            user_id="test_user",
            conversation_id="test_conv",
            tools=["tool1", "tool2"],
            identity="test_identity",
            token_limit=12345,
            compact_threshold=67890,
            enable_rolling_summary=True,
            rolling_summary_threshold=5,
        )
        config.api_keys = {"some_key": "some_value"}  # Should not be in to_dict

        config_dict = config.to_dict()

    assert config_dict["provider"] == "test_provider"
    assert config_dict["model"] == "test_model"
    assert config_dict["mode"] == "test_mode"
    assert config_dict["user_id"] == "test_user"
    assert config_dict["conversation_id"] == "test_conv"
    assert config_dict["tools"] == ["tool1", "tool2"]
    assert config_dict["identity"] == "test_identity"
    assert config_dict["token_limit"] == 12345
    assert config_dict["compact_threshold"] == 67890
    assert config_dict["enable_rolling_summary"] is True
    assert config_dict["rolling_summary_threshold"] == 5
    assert "api_keys" not in config_dict
    assert "config_dir" not in config_dict
    assert "config_file" not in config_dict


def test_from_dict():
    """Test Config.from_dict() method."""
    with patch.object(Config, "load", lambda self: None):
        config_data = {
            "provider": "from_dict_provider",
            "model": "from_dict_model",
            "mode": "from_dict_mode",
            "user_id": "from_dict_user",
            "conversation_id": "from_dict_conv",
            "tools": ["tool_a", "tool_b"],
            "identity": "from_dict_identity",
            "token_limit": 54321,
            "compact_threshold": 98765,
            "enable_rolling_summary": False,
            "rolling_summary_threshold": 15,
            "extra_key": "should_be_ignored",  # Test filtering of extra keys
        }

        config = Config.from_dict(config_data)

    assert config.provider == "from_dict_provider"
    assert config.model == "from_dict_model"
    assert config.mode == "from_dict_mode"
    assert config.user_id == "from_dict_user"
    assert config.conversation_id == "from_dict_conv"
    assert config.tools == ["tool_a", "tool_b"]
    assert config.identity == "from_dict_identity"
    assert config.token_limit == 54321
    assert config.compact_threshold == 98765
    assert config.enable_rolling_summary is False
    assert config.rolling_summary_threshold == 15
    # Ensure extra keys are ignored and default values for non-provided fields are set
    assert config.api_keys == {}
    assert isinstance(config.config_dir, Path)
    assert isinstance(config.config_file, Path)
