"""Test the event stream renderer."""

from unittest.mock import MagicMock, patch

import pytest

from cc.render import Renderer
from cc.render.color import C


@pytest.fixture
def mock_config():
    """Provides a mock config object for the renderer."""
    config = MagicMock()
    config.enable_rolling_summary = False
    config.model = "glm-4.6"
    config.provider = "glm"
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
        f"{C.GRAY}0.0k tokens · 0 msgs · 0 tools · {mock_config.model}{C.R}\n"
        f"{C.GRAY}~{C.R} {C.GRAY}First, I will ponder.{C.R}\n"
        f"{C.MAGENTA}›{C.R} Then, I will answer.\n"
    )
    assert captured.out.strip() == expected_output.strip()


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_tool_call_replaces_spinner_line(capsys, mock_config):
    """Test that tool result replaces the call line, not appends."""
    events = [
        {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'},
        {"type": "result", "payload": {"outcome": "Listed 121 items"}},
        {"type": "end"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    # After \r overwrite, only final result should be visible on that line
    final = captured.out.split("\r")[-1]
    assert "○" not in final  # Call symbol should be overwritten
    assert "●" in final  # Result symbol should be visible
    assert "121 items" in final


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
@pytest.mark.parametrize(
    "msg,error,symbol_char",
    [
        ("25 lines", False, "●"),
        ("File not found", True, "✗"),
    ],
)
async def test_tool_result_rendering(capsys, mock_config, msg, error, symbol_char):
    """Test rendering tool calls with success and error results."""
    events = [
        {"type": "call", "content": '{"name": "read", "args": {"path": "test.py"}}'},
        {"type": "execute"},
        {"type": "result", "payload": {"error": error, "outcome": msg}},
        {"type": "end"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    assert symbol_char in captured.out
    assert msg in captured.out


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
async def test_word_boundary_preserved(capsys, mock_config):
    """Paragraph breaks between chunks are preserved."""
    events = [
        {"type": "respond", "content": "Assessment\n\n"},
        {"type": "respond", "content": "Cogency demonstrates"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    assert "Assessment\n\nCogency demonstrates" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_markdown_bold_rendering(capsys, mock_config):
    """Test that markdown bold is rendered correctly."""
    events = [
        {"type": "respond", "content": "This is **bold text**."},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    expected_output = (
        f"{C.GRAY}0.0k tokens · 0 msgs · 0 tools · glm-4.6{C.R}\n"
        f"{C.MAGENTA}›{C.R} This is {C.BOLD}bold text{C.R}.\n"
    )
    assert captured.out.strip() == expected_output.strip()




@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_header_rendering_with_metric(capsys, mock_config):
    """Test that the header correctly renders the token count from the latest_metric."""
    latest_metric = {
        "total": {"input": 500, "output": 1500},
    }
    events = [{"type": "think", "content": "..."}]
    stream = generate_events(events)
    renderer = Renderer(latest_metric=latest_metric, config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    output_lines = captured.out.strip().split("\n")
    assert output_lines[0] == f"{C.GRAY}2.0k tokens · 0 msgs · 0 tools · {mock_config.model}{C.R}"


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_newline_in_first_token(capsys, mock_config):
    """Test that newlines in the first token are handled correctly."""
    events = [
        {"type": "respond", "content": "Yes\n"},
        {"type": "respond", "content": ", the answer is 42."},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    output_lines = captured.out.strip().split("\n")
    assert len(output_lines) >= 2
    assert output_lines[-1] == ", the answer is 42."
    assert f"{C.MAGENTA}›{C.R} Yes" in output_lines[-2]


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_think_after_result(capsys, mock_config):
    """Test that think events after result events are rendered."""
    events = [
        {"type": "call", "content": '{"name": "read", "args": {"path": "test.py"}}'},
        {"type": "result", "payload": {"outcome": "Read test.py"}},
        {"type": "think", "content": "Now analyzing the code"},
        {"type": "respond", "content": "Found the issue"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    assert "Now analyzing the code" in captured.out
    assert "Found the issue" in captured.out
