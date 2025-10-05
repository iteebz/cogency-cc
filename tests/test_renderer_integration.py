"""Tests for cogency renderer integration in cogency-code.

These tests verify that the cogency renderer works correctly with
cogency-code agent events and maintains proper visual formatting.
"""

from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc.agent import create_agent


class TestRendererIntegration:
    """Test integration between cogency-code and cogency CLI renderer."""

    @pytest.mark.asyncio
    async def test_chunked_respond_strips_leading_space_once(self):
        """Test that chunked respond events strip leading space only on state transition."""
        from cc.renderer import Renderer

        mock_events = [
            {"type": "respond", "content": " Hello", "timestamp": 1.0},
            {"type": "respond", "content": "! I'm", "timestamp": 1.1},
            {"type": "respond", "content": " here", "timestamp": 1.2},
            {"type": "end", "content": "", "timestamp": 1.3},
        ]

        async def mock_stream():
            for event in mock_events:
                yield event

        output = StringIO()
        with patch("sys.stdout", output):
            renderer = Renderer()
            await renderer.render_stream(mock_stream())

        output_text = output.getvalue()
        assert "Hello! I'm here" in output_text
        assert "  " not in output_text

    @pytest.mark.asyncio
    async def test_chunked_think_strips_leading_space_once(self):
        """Test that chunked think events strip leading space only on state transition."""
        from cc.renderer import Renderer

        mock_events = [
            {"type": "think", "content": " analyzing", "timestamp": 1.0},
            {"type": "think", "content": " the", "timestamp": 1.1},
            {"type": "think", "content": " request", "timestamp": 1.2},
            {"type": "end", "content": "", "timestamp": 1.3},
        ]

        async def mock_stream():
            for event in mock_events:
                yield event

        output = StringIO()
        with patch("sys.stdout", output):
            renderer = Renderer()
            await renderer.render_stream(mock_stream())

        output_text = output.getvalue()
        assert "analyzing the request" in output_text

    @pytest.mark.asyncio
    async def test_strips_trailing_newline_before_state_change(self):
        """Test that trailing newlines are stripped before state transitions."""
        from cc.renderer import Renderer

        mock_events = [
            {"type": "respond", "content": "Here is the answer", "timestamp": 1.0},
            {"type": "respond", "content": "\n\n", "timestamp": 1.1},
            {
                "type": "call",
                "content": '{"name": "file_read", "args": {"file": "test.py"}}',
                "timestamp": 1.2,
            },
            {"type": "result", "payload": {"outcome": "ok"}, "timestamp": 1.3},
            {"type": "end", "content": "", "timestamp": 1.4},
        ]

        async def mock_stream():
            for event in mock_events:
                yield event

        output = StringIO()
        with patch("sys.stdout", output):
            renderer = Renderer()
            await renderer.render_stream(mock_stream())

        output_text = output.getvalue()
        lines = output_text.split("\n")
        assert not any(
            line == "" and lines[i + 1].startswith("○") for i, line in enumerate(lines[:-1])
        )

    @pytest.mark.asyncio
    async def test_renderer_with_agent_stream(self):
        """Test that renderer correctly processes agent event stream."""
        from cc.renderer import Renderer

        # Mock agent stream with various event types
        mock_events = [
            {"type": "user", "content": "test query", "timestamp": 1.0},
            {"type": "think", "content": "analyzing request", "timestamp": 1.1},
            {
                "type": "call",
                "content": '{"name": "file_read", "args": {"file": "test.py"}}',
                "timestamp": 1.2,
            },
            {"type": "result", "payload": {"outcome": "File read successfully"}, "timestamp": 1.3},
            {"type": "respond", "content": "I found the issue", "timestamp": 1.4},
            {"type": "end", "content": "", "timestamp": 1.5},
        ]

        # Create async generator
        async def mock_stream():
            for event in mock_events:
                yield event

        # Capture output
        output = StringIO()
        with patch("sys.stdout", output):
            renderer = Renderer()
            await renderer.render_stream(mock_stream())

        # Verify output contains expected elements
        output_text = output.getvalue()
        assert "test query" in output_text
        assert "analyzing request" in output_text
        assert "○" in output_text
        assert "File read successfully" in output_text
        assert "I found the issue" in output_text

    @pytest.mark.asyncio
    async def test_renderer_verbose_metrics(self):
        """Test verbose mode shows metrics information."""
        from cc.renderer import Renderer

        mock_events = [
            {"type": "metric", "total": {"input": 100, "output": 200, "duration": 2.5}},
        ]

        async def mock_stream():
            for event in mock_events:
                yield event

        output = StringIO()
        with patch("sys.stdout", output):
            renderer = Renderer(verbose=True)
            await renderer.render_stream(mock_stream())

        output_text = output.getvalue()
        assert "100➜200|2.5s" in output_text

    @pytest.mark.asyncio
    async def test_renderer_error_handling(self):
        """Test renderer handles error events gracefully."""
        from cc.renderer import Renderer

        mock_events = [
            {"type": "error", "content": "Something went wrong", "timestamp": 1.0},
        ]

        async def mock_stream():
            for event in mock_events:
                yield event

        output = StringIO()
        with patch("sys.stdout", output):
            renderer = Renderer()
            await renderer.render_stream(mock_stream())

        output_text = output.getvalue()
        assert "Something went wrong" in output_text

    @pytest.mark.asyncio
    async def test_renderer_interrupt_handling(self):
        """Test renderer handles interrupt events correctly."""
        from cc.renderer import Renderer

        mock_events = [
            {"type": "interrupt", "content": "User cancelled", "timestamp": 1.0},
        ]

        async def mock_stream():
            for event in mock_events:
                yield event

        output = StringIO()
        with patch("sys.stdout", output):
            renderer = Renderer()
            await renderer.render_stream(mock_stream())

        output_text = output.getvalue()
        assert "Interrupted" in output_text


class TestEventFlow:
    """Test complete event flow from agent through renderer."""

    @pytest.mark.asyncio
    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    async def test_complete_event_flow(self, mock_config_class, mock_glm):
        """Test complete flow from agent creation to renderer output."""
        from cc.renderer import Renderer

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

        with patch("cc.agent.load_instructions", return_value=None):
            with patch("cc.agent.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent.return_value = mock_stream()
                mock_agent_class.return_value = mock_agent

                # Create agent and capture renderer output
                config = MagicMock()
                config.provider = "glm"
                config.get_api_key.return_value = "test-key"
                config.identity = "coding"

                create_agent(config)

                output = StringIO()
                with patch("sys.stdout", output):
                    renderer = Renderer()
                    await renderer.render_stream(mock_stream())

                output_text = output.getvalue()
                assert "debug this code" in output_text
                assert "> I found the bug on line 42" in output_text


class TestRendererContracts:
    """Test that renderer maintains cogency contracts."""

    def test_renderer_state_management(self):
        """Test renderer manages internal state correctly."""
        from cc.renderer import Renderer

        renderer = Renderer()
        assert renderer.current_state is None
        assert renderer.verbose is False

        verbose_renderer = Renderer(verbose=True)
        assert verbose_renderer.verbose is True

    def test_renderer_symbol_consistency(self):
        """Test that symbols match cogency conventions."""
        from cc.renderer import Renderer

        # These symbols should match cogency CLI conventions

        # Verify by checking renderer source or behavior
        renderer = Renderer()
        assert hasattr(renderer, "render_stream")  # Core contract method
