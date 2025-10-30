"""Tests for conversation export functionality."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc.commands.export import export_conversation


@pytest.mark.asyncio
async def test_export_no_conversation_id_uses_last():
    """Should use last conversation when no ID specified."""
    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(
        return_value=[
            {"type": "user", "content": "test query", "timestamp": 1234567890},
            {"type": "respond", "content": "test response"},
        ]
    )

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("cc.commands.export.get_last_conversation", return_value="conv123"),
        patch("builtins.print") as mock_print,
    ):
        await export_conversation(config=mock_config, conversation_id=None, format="json")

        # Should load last conversation
        mock_storage.load_messages.assert_called_once_with("conv123", "test-user")
        assert mock_print.called


@pytest.mark.asyncio
async def test_export_json_format():
    """Should export raw messages as JSON when format=json."""
    messages = [
        {"type": "user", "content": "test query", "timestamp": 1234567890},
        {"type": "respond", "content": "test response"},
    ]

    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=messages)

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("builtins.print") as mock_print,
    ):
        await export_conversation(config=mock_config, conversation_id="conv123", format="json")

        # Should print JSON
        printed = mock_print.call_args[0][0]
        parsed = json.loads(printed)
        assert parsed == messages


@pytest.mark.asyncio
async def test_export_markdown_format():
    """Should render events as markdown when format=markdown."""
    messages = [
        {"type": "user", "content": "test query", "timestamp": 1234567890},
        {"type": "respond", "content": "test response"},
    ]

    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=messages)

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("cc.commands.export.render_messages_to_string") as mock_render,
        patch("builtins.print") as mock_print,
    ):
        mock_render.return_value = "rendered output"

        await export_conversation(config=mock_config, conversation_id="conv123", format="markdown")

        # Should render messages
        mock_render.assert_called_once_with(messages, mock_config, no_color=False)

        # Should include header with metadata
        printed = mock_print.call_args[0][0]
        assert "# Conversation Export" in printed
        assert "conv123" in printed
        assert "rendered output" in printed


@pytest.mark.asyncio
async def test_export_to_file():
    """Should write to file when output path specified."""
    messages = [
        {"type": "user", "content": "test query", "timestamp": 1234567890},
        {"type": "respond", "content": "test response"},
    ]

    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=messages)

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("cc.commands.export.render_messages_to_string") as mock_render,
        patch("pathlib.Path.write_text") as mock_write,
        patch("builtins.print") as mock_print,
    ):
        mock_render.return_value = "rendered output"

        await export_conversation(
            config=mock_config,
            conversation_id="conv123",
            format="markdown",
            output="export.md",
        )

        # Should write to file
        assert mock_write.called
        written_content = mock_write.call_args[0][0]
        assert "# Conversation Export" in written_content
        assert "rendered output" in written_content

        # Should print confirmation, not content
        printed = mock_print.call_args[0][0]
        assert "export.md" in printed.lower()


@pytest.mark.asyncio
async def test_export_no_color_option():
    """Should strip ANSI codes when --no-color specified."""
    messages = [{"type": "user", "content": "test"}]

    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=messages)

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("cc.commands.export.render_messages_to_string") as mock_render,
        patch("builtins.print"),
    ):
        await export_conversation(
            config=mock_config, conversation_id="conv123", format="markdown", no_color=True
        )

        # Should pass no_color flag to renderer
        call_kwargs = mock_render.call_args[1] if len(mock_render.call_args) > 1 else {}
        assert call_kwargs.get("no_color") is True


@pytest.mark.asyncio
async def test_export_empty_conversation():
    """Should handle empty conversations gracefully."""
    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=[])

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("builtins.print") as mock_print,
    ):
        await export_conversation(config=mock_config, conversation_id="conv123", format="markdown")

        # Should print empty message
        printed = mock_print.call_args[0][0]
        assert "no messages" in printed.lower() or "empty" in printed.lower()


@pytest.mark.asyncio
async def test_export_conversation_id_priority():
    """Should use explicit conversation ID over last conversation."""
    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=[{"type": "user", "content": "test"}])

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("cc.commands.export.get_last_conversation", return_value="conv-last"),
        patch("cc.commands.export.render_messages_to_string", return_value="output"),
        patch("builtins.print"),
    ):
        await export_conversation(
            config=mock_config, conversation_id="conv-explicit", format="markdown"
        )

        # Should use explicit ID, not last
        mock_storage.load_messages.assert_called_once_with("conv-explicit", "test-user")


@pytest.mark.asyncio
async def test_export_includes_metadata():
    """Should include timestamp and message count in export."""
    messages = [
        {"type": "user", "content": "first", "timestamp": 1234567890},
        {"type": "respond", "content": "response"},
        {"type": "user", "content": "second", "timestamp": 1234567900},
    ]

    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=messages)

    mock_config = MagicMock()
    mock_config.user_id = "test-user"
    mock_config.config_dir = Path(".cogency")

    with (
        patch("cc.commands.export.get_storage", return_value=mock_storage),
        patch("cc.commands.export.render_messages_to_string", return_value="rendered"),
        patch("builtins.print") as mock_print,
    ):
        await export_conversation(config=mock_config, conversation_id="conv123", format="markdown")

        printed = mock_print.call_args[0][0]
        # Should include ID
        assert "conv123" in printed
        # Should include timestamp from first message
        assert "1234567890" in printed or "2009" in printed  # Either raw or formatted
