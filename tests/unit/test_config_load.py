"""Test Config.load_or_default() behavior."""

import json
import tempfile
from pathlib import Path

import pytest

from cc.config import Config


def test_load_or_default_with_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".cogency"
        config = Config.load_or_default(config_dir=config_dir)

        assert config.user_id == "cc_user"
        assert config.provider == "glm"


def test_load_or_default_with_existing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".cogency"
        config_dir.mkdir()
        config_file = config_dir / "cc.json"

        config_file.write_text(
            json.dumps({"user_id": "test_user", "provider": "openai", "model": "gpt-4"})
        )

        config = Config()
        config.config_dir = config_dir
        config.config_file = config_file
        config.load()

        assert config.user_id == "test_user"
        assert config.provider == "openai"
        assert config.model == "gpt-4"


def test_load_raises_on_invalid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".cogency"
        config_dir.mkdir()
        config_file = config_dir / "cc.json"

        config_file.write_text("invalid json{")

        config = Config()
        config.config_dir = config_dir
        config.config_file = config_file

        with pytest.raises(json.JSONDecodeError):
            config.load()
