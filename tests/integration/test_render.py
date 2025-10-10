"""Tests for cogency renderer integration in cogency-cc."""

from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc.agent import create_agent


@pytest.mark.asyncio
@patch("cc.agent.GLM")
@patch("cc.agent.Config")
async def test_event_flow(mock_config_class, mock_glm):
    """Test complete flow from agent creation to renderer output."""
    from cc.render import Renderer

    # Setup agent mock
    mock_config = MagicMock()
    mock_config.provider = "glm"
    mock_config.get_api_key.return_value = "test-key"
    mock_config_class.return_value = mock_config
    mock_glm.return_value = MagicMock()

    # Mock agent stream
    mock_events = [
        {"type": "user", "content": "debug this code", "timestamp": 1.0},
        {"type": "respond", "content": "I found the bug on line 42", "timestamp": 1.1},
    ]

    async def mock_stream():
        for event in mock_events:
            yield event

    with patch("cc.cc_md.load", return_value=None):
        with patch("cc.agent.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.return_value = mock_stream()
            mock_agent_class.return_value = mock_agent

            # Create agent and capture renderer output
            config = MagicMock()
            config.provider = "glm"
            config.get_api_key.return_value = "test-key"
            config.identity = "code"

            create_agent(config)

            output = StringIO()
            with patch("sys.stdout", output):
                renderer = Renderer()
                await renderer.render_stream(mock_stream())

            output_text = output.getvalue()
            assert "debug this code" in output_text
            assert "I found the bug on line 42" in output_text
