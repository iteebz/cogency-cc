"""Test the event stream renderer."""

from unittest.mock import MagicMock, patch

import pytest

from cc.lib.color import C
from cc.renderer import Renderer


@pytest.fixture
def mock_config():
    """Provides a mock config object for the renderer."""
    config = MagicMock()
    config.enable_rolling_summary = False
    return config


async def generate_events(events):
    """An async generator to yield a list of events."""
    for event in events:
        yield event


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})  # Disable spinners for deterministic output
async def test_think_and_respond(capsys, mock_config):
    """Test rendering of a simple think -> respond sequence."""
    events = [
        {"type": "think", "content": "First, I will ponder."},
        {"type": "respond", "content": "Then, I will answer."},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    expected_output = (
        f"\n{C.GRAY}~{C.R} First, I will ponder.\n{C.MAGENTA}›{C.R} Then, I will answer."
    )
    assert captured.out.strip() == expected_output.strip()


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_tool_call_and_result(capsys, mock_config):
    """Test rendering of a tool call and its successful result."""
    events = [
        {"type": "call", "content": '{"name": "file_read", "args": {"path": "test.py"}}'},
        {"type": "execute"},
        {"type": "result", "payload": {"outcome": "Read test.py (25 lines)"}},
        {"type": "end"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    expected_output = (
        f"\n{C.GRAY}○{C.R} {C.GRAY}file_read(test.py): ...{C.R}"
        f"\r\033[K{C.GREEN}●{C.R} file_read(test.py): +25 lines\n"
        "\n\n"
    )
    # We strip because the final newline handling can be tricky
    assert captured.out.strip() == expected_output.strip()


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_tool_call_with_error(capsys, mock_config):
    """Test rendering of a tool call that results in an error."""
    events = [
        {"type": "call", "content": '{"name": "file_read", "args": {"path": "nonexistent.py"}}'},
        {"type": "execute"},
        {
            "type": "result",
            "payload": {"error": True, "outcome": "File not found"},
        },
        {"type": "end"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    expected_output = (
        f"\n{C.GRAY}○{C.R} {C.GRAY}file_read(nonexistent.py): ...{C.R}"
        f"\r\033[K{C.RED}✗{C.R} file_read(nonexistent.py): File not found\n"
        "\n\n"
    )
    assert captured.out.strip() == expected_output.strip()


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_stream_error(capsys, mock_config):
    """Test that an error in the stream itself is rendered correctly."""

    async def error_stream():
        yield {"type": "think", "content": "I am thinking..."}
        raise ValueError("Something went wrong")

    renderer = Renderer(config=mock_config)

    with pytest.raises(ValueError, match="Something went wrong"):
        await renderer.render_stream(error_stream())

    captured = capsys.readouterr()
    assert f"\n{C.RED}✗ Stream error: Something went wrong{C.R}" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_direct_error_event(capsys, mock_config):
    """Test rendering of an explicit 'error' event."""
    events = [{"type": "error", "payload": {"error": "Invalid API key"}}]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    assert f"{C.RED}✗{C.R} Invalid API key" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_interrupt_event(capsys, mock_config):
    """Test rendering of an explicit 'interrupt' event."""
    events = [{"type": "interrupt"}]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    assert f"{C.YELLOW}⚠{C.R} Interrupted" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_header_rendering(capsys, mock_config):
    messages = [
        {"type": "user", "content": "hello"},
        {"type": "call", "content": "..."},
        {"type": "metric", "total": {"input": 100, "output": 200}},
    ]
    events = [{"type": "think", "content": "..."}]
    stream = generate_events(events)
    renderer = Renderer(messages=messages, config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    assert "» 3 msgs | 1 calls | 100→200 tok" in captured.out
