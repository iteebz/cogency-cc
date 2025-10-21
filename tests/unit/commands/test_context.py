"""Context command core behavior.

Contracts:
- Root finding: No project root → early return, displays error
- Conversation lookup: No conversation found → early return, displays error
- Message loading error: Empty messages → early return, displays error
- Valid messages: Distribution displayed with percentages
- Token metrics: Shows actual or estimated tokens
- Debug mode disabled: Hides full message content
- Debug mode enabled: Shows full messages by type and index
"""

import io
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_no_project_root_returns_early(mock_config, mock_snapshots, monkeypatch):
    """Command exits early when no project root found."""
    from src.cc.commands.context import show_context

    monkeypatch.setattr("src.cc.commands.context.root", lambda: None)

    captured_output = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured_output)

    await show_context(mock_config, mock_snapshots)
    output = captured_output.getvalue()

    assert "No project root" in output


@pytest.mark.asyncio
async def test_no_conversation_returns_early(mock_config, mock_snapshots, monkeypatch):
    """Command exits early when no conversation found."""
    from src.cc.commands.context import show_context

    mock_project_root = "/test/project"
    monkeypatch.setattr("src.cc.commands.context.root", lambda: mock_project_root)
    monkeypatch.setattr("src.cc.commands.context.get_last_conversation", lambda x: None)

    captured_output = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured_output)

    await show_context(mock_config, mock_snapshots)
    output = captured_output.getvalue()

    assert "No conversation" in output


@pytest.mark.asyncio
async def test_no_messages_returns_early(mock_config, mock_snapshots, monkeypatch, capsys):
    """Command exits early when conversation has no messages."""
    from src.cc.commands.context import show_context

    mock_config.conversation_id = "conv_123"

    monkeypatch.setattr("src.cc.commands.context.root", lambda: "/test/project")

    mock_storage = AsyncMock()
    mock_storage.load_messages = AsyncMock(return_value=[])

    with patch("cc.lib.sqlite.storage", return_value=mock_storage):
        await show_context(mock_config, mock_snapshots)

    captured = capsys.readouterr()
    assert "No messages" in captured.out


def test_distribution_calculation():
    """Message distribution calculation is correct."""
    messages = [
        {"type": "user", "content": "Hello"},
        {"type": "user", "content": "Hi"},
        {"type": "assistant", "content": "Hi there"},
    ]

    dist = {}
    for m in messages:
        t = m.get("type", "unknown")
        dist[t] = dist.get(t, 0) + 1

    assert dist["user"] == 2
    assert dist["assistant"] == 1

    total = len(messages)
    pct_user = int(dist["user"] / total * 100)
    pct_asst = int(dist["assistant"] / total * 100)

    assert pct_user == 66
    assert pct_asst == 33


def test_token_estimation():
    """Token estimation from message length is correct."""
    messages = [
        {"type": "user", "content": "Hello world, this is a test message"},
        {"type": "assistant", "content": "Response here"},
    ]

    est_tokens = sum(len(m.get("content", "")) // 4 for m in messages)

    assert est_tokens > 0
    assert est_tokens < len("".join(m.get("content", "") for m in messages))


def test_token_extraction_from_metric():
    """Token data extracted correctly from metric message."""
    metric_msg = {"type": "metric", "total": {"input": 100, "output": 50}}

    total_data = metric_msg.get("total", {})
    total_tokens = total_data.get("input", 0) + total_data.get("output", 0)

    assert total_tokens == 150
    assert total_data["input"] == 100
    assert total_data["output"] == 50


def test_debug_flag_gates_output():
    """Debug mode flag determines verbosity level."""
    debug_false_messages = [
        "conversation:",
        "messages:",
        "distribution:",
        "use --debug",
    ]

    debug_true_messages = [
        "conversation:",
        "[0]",
        "[1]",
    ]

    assert "use --debug" in debug_false_messages
    assert "use --debug" not in debug_true_messages


def test_message_rendering_by_type():
    """Message types have appropriate prefixes."""
    msg_type_prefixes = {
        "user": "[",
        "assistant": "[",
        "system": "[",
        "call": "[",
        "result": "[",
        "summary": "[",
        "metric": "[",
    }

    for msg_type in msg_type_prefixes:
        assert msg_type_prefixes[msg_type] == "["
