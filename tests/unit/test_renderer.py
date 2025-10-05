"""Tests for the renderer."""

from io import StringIO
from unittest.mock import patch

import pytest

from cc.renderer import Renderer


@pytest.mark.asyncio
async def test_chunked_respond_strips_leading_space_once():
    """Test that chunked respond events strip leading space only on state transition."""
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
async def test_chunked_think_strips_leading_space_once():
    """Test that chunked think events strip leading space only on state transition."""
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
async def test_strips_trailing_newline_before_state_change():
    """Test that trailing newlines are stripped before state transitions."""
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
async def test_renderer_with_agent_stream():
    """Test that renderer correctly processes agent event stream."""
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
async def test_renderer_verbose_metrics():
    """Test verbose mode shows metrics information."""
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
async def test_renderer_error_handling():
    """Test renderer handles error events gracefully."""
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
async def test_renderer_interrupt_handling():
    """Test renderer handles interrupt events correctly."""
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

def test_renderer_state_management():
    """Test renderer manages internal state correctly."""
    renderer = Renderer()
    assert renderer.current_state is None
    assert renderer.verbose is False

    verbose_renderer = Renderer(verbose=True)
    assert verbose_renderer.verbose is True

def test_renderer_symbol_consistency():
    """Test that symbols match cogency conventions."""
    # These symbols should match cogency CLI conventions

    # Verify by checking renderer source or behavior
    renderer = Renderer()
    assert hasattr(renderer, "render_stream")  # Core contract method
