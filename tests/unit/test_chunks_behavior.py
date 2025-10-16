"""Tests for chunk behavior in cogency-cc.

Verify that:
1. Chunks are enabled by default for all models except codex
2. Codex models use generate mode instead
3. Renderer immediately displays think and respond chunks
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc.cli import run_agent
from cc.render import Renderer
from cc.render.color import C


@pytest.mark.asyncio
async def test_chunks_enabled_by_default_non_codex():
    """Contract: Chunks enabled by default for non-codex models."""
    mock_agent = MagicMock()
    mock_agent.config.llm.http_model = "gpt-4"
    mock_agent.config.llm.close = AsyncMock()
    mock_config = MagicMock()
    mock_config.user_id = "test_user"

    mock_storage = MagicMock()
    mock_storage.load_messages = AsyncMock(return_value=[])
    mock_storage.load_latest_metric = AsyncMock(return_value=None)

    async def mock_stream():
        yield {"type": "end"}

    mock_agent.return_value = mock_stream()
    mock_renderer = AsyncMock()

    with patch("cc.lib.sqlite.storage", return_value=mock_storage):
        with patch("cc.cli.Renderer", return_value=mock_renderer):
            await run_agent(
                agent=mock_agent,
                query="test",
                conv_id="conv-123",
                config=mock_config,
            )

            # Verify agent was called with chunks=True
            mock_agent.assert_called_once()
            call_kwargs = mock_agent.call_args[1]
            assert call_kwargs.get("chunks") is True
            assert call_kwargs.get("generate") is False


@pytest.mark.asyncio
async def test_chunks_disabled_for_codex():
    """Contract: Chunks disabled and generate enabled for codex models."""
    mock_agent = MagicMock()
    mock_agent.config.llm.http_model = "codex"
    mock_agent.config.llm.close = AsyncMock()
    mock_config = MagicMock()
    mock_config.user_id = "test_user"

    mock_storage = MagicMock()
    mock_storage.load_messages = AsyncMock(return_value=[])
    mock_storage.load_latest_metric = AsyncMock(return_value=None)

    async def mock_stream():
        yield {"type": "end"}

    mock_agent.return_value = mock_stream()
    mock_renderer = AsyncMock()

    with patch("cc.lib.sqlite.storage", return_value=mock_storage):
        with patch("cc.cli.Renderer", return_value=mock_renderer):
            await run_agent(
                agent=mock_agent,
                query="test",
                conv_id="conv-123",
                config=mock_config,
            )

            # Verify agent was called with chunks=False, generate=True
            mock_agent.assert_called_once()
            call_kwargs = mock_agent.call_args[1]
            assert call_kwargs.get("chunks") is False
            assert call_kwargs.get("generate") is True


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_renderer_immediately_displays_think_chunks(capsys):
    """Contract: Renderer immediately outputs think chunks without buffering."""

    async def generate_think_events():
        yield {"type": "think", "content": "Thinking step 1"}
        yield {"type": "think", "content": " continuing..."}

    config = MagicMock()
    config.model = "gpt-4"
    renderer = Renderer(config=config)

    await renderer.render_stream(generate_think_events())

    captured = capsys.readouterr()
    # Verify think chunks appear with gray color and ~ prefix
    assert f"{C.GRAY}~{C.R}" in captured.out
    assert "Thinking step 1" in captured.out
    assert "continuing..." in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_renderer_immediately_displays_respond_chunks(capsys):
    """Contract: Renderer immediately outputs respond chunks without buffering."""

    async def generate_respond_events():
        yield {"type": "respond", "content": "Here is "}
        yield {"type": "respond", "content": "the answer"}

    config = MagicMock()
    config.model = "gpt-4"
    renderer = Renderer(config=config)

    await renderer.render_stream(generate_respond_events())

    captured = capsys.readouterr()
    # Verify respond chunks appear with magenta prefix
    assert f"{C.MAGENTA}›{C.R}" in captured.out
    assert "Here is" in captured.out
    assert "the answer" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_renderer_interleaves_think_and_respond(capsys):
    """Contract: Renderer handles interleaved think and respond chunks correctly."""

    async def generate_mixed_events():
        yield {"type": "think", "content": "Let me think"}
        yield {"type": "respond", "content": "The answer is: "}
        yield {"type": "respond", "content": "42"}

    config = MagicMock()
    config.model = "gpt-4"
    renderer = Renderer(config=config)

    await renderer.render_stream(generate_mixed_events())

    captured = capsys.readouterr()
    # Both think and respond should be visible
    assert f"{C.GRAY}~{C.R}" in captured.out
    assert "Let me think" in captured.out
    assert f"{C.MAGENTA}›{C.R}" in captured.out
    assert "The answer is:" in captured.out
    assert "42" in captured.out
