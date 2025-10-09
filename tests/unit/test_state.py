"""Test configuration state management."""

from pathlib import Path
from unittest.mock import patch

import pytest

from cc.state import Config, _default_config_dir


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory for testing."""
    return tmp_path / ".cogency"


def test_config_initialization_defaults():
    config = Config()
    assert config.provider == "glm"
    assert config.model is None
    assert config.user_id == "new_user"


def test_config_post_init_sets_correct_path(temp_config_dir: Path):
    """Test that __post_init__ correctly constructs the config_file path."""
    config = Config(config_dir=temp_config_dir)
    assert config.config_file == temp_config_dir / "cc.json"


def test_save_and_load_cycle(temp_config_dir: Path):
    config_save = Config(config_dir=temp_config_dir)
    config_save.provider = "openai"
    config_save.model = "gpt-5-codex-low"
    config_save.user_id = "test_user"
    config_save.save()

    assert config_save.config_file.exists()

    config_load = Config(config_dir=temp_config_dir)
    config_load.load()

    assert config_load.provider == "openai"
    assert config_load.model == "gpt-5-codex-low"
    assert config_load.user_id == "test_user"


def test_load_from_non_existent_file(temp_config_dir: Path):
    """Test that loading from a non-existent file results in default values."""
    config = Config(config_dir=temp_config_dir)
    # Ensure the file doesn't exist
    assert not config.config_file.exists()

    config.load()

    # Assert that the config retains its default values
    assert config.provider == "glm"
    assert config.model is None


def test_load_from_corrupted_json(temp_config_dir: Path, capsys):
    """Test that loading from a corrupted JSON file handles the error gracefully."""
    config_dir = temp_config_dir
    config_file = config_dir / "cc.json"
    config_dir.mkdir()
    config_file.write_text("this is not valid json")

    config = Config(config_dir=config_dir)
    config.load()

    # Assert that the config retains its default values
    assert config.provider == "glm"
    assert config.model is None

    # Assert that a warning was printed to stderr
    stderr = capsys.readouterr().err
    assert "Warning: Could not load config" in stderr
    assert "Expecting value: line 1 column 1 (char 0)" in stderr


def test_update_method_changes_and_saves(temp_config_dir: Path):
    """Test that the update method modifies attributes and persists the changes."""
    config = Config(config_dir=temp_config_dir)
    config.update(provider="anthropic", model="claude-3.5-sonnet")

    assert config.provider == "anthropic"
    assert config.model == "claude-3.5-sonnet"

    # Verify that the changes were saved to the file
    config_load = Config(config_dir=temp_config_dir)
    config_load.load()
    assert config_load.provider == "anthropic"
    assert config_load.model == "claude-3.5-sonnet"


def test_get_api_key_priority(temp_config_dir: Path):
    """Test the priority of API key retrieval: env > saved keys."""
    config = Config(config_dir=temp_config_dir)
    config.api_keys = {"openai": "saved-key"}
    config.save()

    # 1. No environment variable, should use saved key
    with patch.dict("os.environ", clear=True):
        with patch("cc.state.rotated_api_key", return_value=None):
            assert config.get_api_key("openai") == "saved-key"

    # 2. With environment variable, should use env key
    with patch("cc.state.rotated_api_key", return_value="env-key"):
        assert config.get_api_key("openai") == "env-key"

    # 3. No key found
    with patch.dict("os.environ", clear=True):
        with patch("cc.state.rotated_api_key", return_value=None):
            assert config.get_api_key("anthropic") is None


def test_get_api_key_status(temp_config_dir: Path):
    """Test the display status for API keys."""
    config = Config(config_dir=temp_config_dir)
    config.api_keys = {"openai": "saved-key"}
    config.save()

    # Env key exists
    with patch("cc.state.rotated_keys", return_value=["env-key"]):
        assert config.get_api_key_status("openai") == "✓ Openai (env)"

    # Only saved key exists
    with patch("cc.state.rotated_keys", return_value=[]):
        assert config.get_api_key_status("openai") == "✓ Openai (saved)"

    # No key exists
    with patch("cc.state.rotated_keys", return_value=[]):
        assert config.get_api_key_status("anthropic") == "✗ Anthropic"


def test_default_config_dir_logic():
    """Test the logic for determining the default config directory."""
    # 1. Override via environment variable
    with patch.dict("os.environ", {"COGENCY_CONFIG_DIR": "/tmp/custom"}):
        assert _default_config_dir() == Path("/tmp/custom/.cogency")

    # 2. Pytest environment
    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "true"}, clear=True):
        assert "cogency-cc-tests" in str(_default_config_dir())

    # 3. Default to home directory
    with patch.dict("os.environ", clear=True):
        with patch("pathlib.Path.home", return_value=Path("/fake/home")):
            with patch("cc.state.Path") as mock_path:
                # Mock Path.cwd() to return a fake directory
                mock_path.cwd.return_value = Path("/fake/cwd")
                # Mock the project-local .cogency directory to not exist
                mock_path.return_value.is_dir.return_value = False
                # Mock Path.home() to return our fake home
                mock_path.home.return_value = Path("/fake/home")

                assert _default_config_dir() == Path("/fake/home/.cogency")
