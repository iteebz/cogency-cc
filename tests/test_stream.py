"""Tests for the stream widget."""

import pytest

from cogency_code.events import render_event
from cogency_code.widgets.stream import StreamView


def test_render_think_event():
    """Test rendering of think events."""
    event = {
        "type": "think",
        "content": "I should check the file",
        "payload": {},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)
    assert rendered is not None
    assert "~ I should check the file" in rendered.plain
    assert rendered.style == "dim italic"


def test_render_respond_event():
    """Test rendering of respond events."""
    event = {
        "type": "respond",
        "content": "The answer is 42",
        "payload": {},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)
    assert rendered is not None
    assert "The answer is 42" in rendered.plain
    assert rendered.style == "bold white"


def test_render_call_event():
    """Test rendering of call events."""
    event = {
        "type": "call",
        "content": "file_read(path='test.py')",
        "payload": {},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)
    assert rendered is not None
    # Should fall back to generic message if parsing fails
    assert "Tool execution" in rendered.plain


def test_render_result_event():
    """Test rendering of result events."""
    event = {
        "type": "result",
        "content": "",
        "payload": {"outcome": "File read successfully"},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)
    assert rendered is not None
    assert "File read successfully" in rendered.plain
    assert "●" in rendered.plain
    assert rendered.style == "green"


def test_render_metrics_event():
    """Test that metrics events return None."""
    event = {"type": "metrics", "content": "", "payload": {"tokens": 100}, "timestamp": 1234567890}

    rendered = render_event(event)
    assert rendered is None


def test_render_end_event():
    """Test rendering of end events."""
    event = {"type": "end", "content": "", "payload": {}, "timestamp": 1234567890}

    rendered = render_event(event)
    assert rendered is not None
    assert "Session ended" in rendered.plain


def test_render_unknown_event():
    """Test rendering of unknown event types."""
    event = {
        "type": "unknown",
        "content": "Something happened",
        "payload": {},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)
    assert rendered is not None
    assert "? Something happened" in rendered.plain


@pytest.mark.asyncio
async def test_stream_view_add_event():
    """Test adding events to the stream view."""
    # For now, just test that the method exists and can be called
    # Full widget testing would require Textual test framework
    stream = StreamView()

    event = {"type": "respond", "content": "Test message", "payload": {}, "timestamp": 0}

    # The method should exist and be callable
    assert hasattr(stream, "add_event")
    assert callable(stream.add_event)

    # We can't fully test without Textual's test framework
    # but we can verify the event renderer works
    from cogency_code.events import render_event

    rendered = render_event(event)
    assert rendered is not None
    assert "Test message" in rendered.plain
