"""Tests for event rendering system."""

from cogency_code.events import render_event


def test_render_think_event_with_content():
    """Test rendering think events with content."""
    event = {
        "type": "think",
        "content": "I should analyze the code structure",
        "payload": {},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)

    assert rendered is not None
    assert "I should analyze the code structure" in rendered.plain
    assert rendered.style == "dim italic"


def test_render_think_event_empty_content():
    """Test rendering think events with empty content."""
    event = {"type": "think", "content": "", "payload": {}, "timestamp": 1234567890}

    rendered = render_event(event)
    assert rendered is None


def test_render_respond_event_with_content():
    """Test rendering respond events with content."""
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


def test_render_respond_event_empty_content():
    """Test rendering respond events with empty content."""
    event = {"type": "respond", "content": "", "payload": {}, "timestamp": 1234567890}

    rendered = render_event(event)
    assert rendered is None


def test_render_call_event_basic():
    """Test rendering call events with basic fallback."""
    event = {"type": "call", "content": "some_tool_call()", "payload": {}, "timestamp": 1234567890}

    rendered = render_event(event)

    assert rendered is not None
    assert "Tool execution" in rendered.plain
    assert rendered.style == "cyan"


def test_render_result_event_with_outcome():
    """Test rendering result events with outcome."""
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


def test_render_result_event_without_outcome():
    """Test rendering result events without outcome."""
    event = {"type": "result", "content": "", "payload": {}, "timestamp": 1234567890}

    rendered = render_event(event)

    assert rendered is not None
    assert "Tool completed" in rendered.plain
    assert rendered.style == "green"


def test_render_metrics_event():
    """Test that metrics events return None."""
    event = {
        "type": "metrics",
        "content": "",
        "payload": {"tokens_in": 100, "tokens_out": 200, "duration": 2.5},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)
    assert rendered is None


def test_render_end_event():
    """Test rendering end events."""
    event = {"type": "end", "content": "", "payload": {}, "timestamp": 1234567890}

    rendered = render_event(event)

    assert rendered is not None
    assert "Session ended" in rendered.plain
    assert rendered.style == "yellow"


def test_render_unknown_event():
    """Test rendering unknown event types."""
    event = {
        "type": "unknown_type",
        "content": "Something unexpected happened",
        "payload": {},
        "timestamp": 1234567890,
    }

    rendered = render_event(event)

    assert rendered is not None
    assert "Something unexpected happened" in rendered.plain
    assert rendered.style == "red"


def test_render_unknown_event_no_content():
    """Test rendering unknown events without content."""
    event = {"type": "unknown_type", "payload": {}, "timestamp": 1234567890}

    rendered = render_event(event)

    assert rendered is not None
    assert "Unknown event" in rendered.plain
    assert rendered.style == "red"


def test_render_event_type_coverage():
    """Test that all event types are handled."""
    event_types = ["user", "think", "respond", "call", "result", "metrics", "end", "unknown"]

    base_event = {"content": "test", "payload": {}, "timestamp": 0}

    for event_type in event_types:
        event = base_event.copy()
        event["type"] = event_type

        rendered = render_event(event)

        if event_type == "metrics":
            assert rendered is None
        else:
            assert rendered is not None
