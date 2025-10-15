"""Test user_id consistency across save/load operations."""

from unittest.mock import patch

import pytest

from cc.agent import create_agent
from cc.state import Config
from tests.conftest import MockLLM


@pytest.mark.asyncio
async def test_user_id_consistency():
    """Ensure messages saved with custom user_id can be loaded back."""
    config = Config(provider="mock", user_id="test_user")

    with patch("cc.agent._create_llm") as mock_create:
        mock_llm = MockLLM()
        mock_create.return_value = mock_llm
        agent = create_agent(config)

        events = []
        async for event in agent(
            query="list files", user_id=config.user_id, conversation_id="test-conv"
        ):
            events.append(event)

        assert len(events) > 0

        from cogency.lib.sqlite import SQLite

        storage = SQLite()
        msgs = await storage.load_messages("test-conv", config.user_id)

        assert len(msgs) > 0
        user_msgs = [m for m in msgs if m.get("type") == "user"]
        assert len(user_msgs) > 0
        assert "list files" in user_msgs[0].get("content", "")


@pytest.mark.asyncio
async def test_default_user_id_is_cc_user():
    """Verify default user_id is 'cc_user'."""
    config = Config()
    assert config.user_id == "cc_user"


@pytest.mark.asyncio
async def test_custom_user_id_persists():
    """Custom user_id should persist through config save/load."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".cogency"
        config_dir.mkdir()

        config = Config(user_id="custom_user")
        config.config_dir = config_dir
        config.config_file = config_dir / "cc.json"
        config.save()

        config2 = Config()
        config2.config_dir = config_dir
        config2.config_file = config_dir / "cc.json"
        config2.load()

        assert config2.user_id == "custom_user"
