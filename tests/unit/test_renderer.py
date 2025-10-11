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
        f"{C.GRAY}0 msgs · 0 tools · glm-4.6{C.R}"
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
        f"{C.GRAY}0 msgs · 0 tools · glm-4.6{C.R}"
        f"\n{C.GRAY}○{C.R} {C.GRAY}file_read(test.py): ...{C.R}"
        f"\r\033[K{C.GREEN}●{C.R} file_read(test.py): +25 lines\n"
        "\n"
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
        f"{C.GRAY}0 msgs · 0 tools · glm-4.6{C.R}"
        f"\n{C.GRAY}○{C.R} {C.GRAY}file_read(nonexistent.py): ...{C.R}"
        f"\r\033[K{C.RED}✗{C.R} file_read(nonexistent.py): File not found\n"
        "\n"
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
    assert "0.3k tokens · 3 msgs · 1 tools · glm-4.6" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_leading_newlines_buffered(capsys, mock_config):
    """Test that leading newlines are buffered until content appears."""
    events = [
        {"type": "respond", "content": "\n\n"},
        {"type": "respond", "content": "Actual content"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    # Should have newlines followed by content, no extra blank lines at start
    assert captured.out.count("\n\n\n") == 0
    assert "Actual content" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_word_boundary_preserved(capsys, mock_config):
    """Test that word boundaries across chunks are preserved."""
    events = [
        {"type": "respond", "content": "Assessment\n\n"},
        {"type": "respond", "content": "Cogency demonstrates"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    assert "Assessment\n\nCogency demonstrates" in captured.out
    assert "AssessmentCogency" not in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_empty_respond_suppressed(capsys, mock_config):
    """Empty respond events should not render prefix."""
    events = [
        {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'},
        {"type": "execute"},
        {"type": "result", "payload": {"outcome": "Listed 10 items"}},
        {"type": "respond", "content": ""},
        {"type": "respond", "content": "Found 10 items"},
        {"type": "end"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    out_lines = [line for line in captured.out.split("\n") if line.strip()]

    empty_respond_lines = [line for line in out_lines if line.strip() == f"{C.MAGENTA}›{C.R}"]
    assert len(empty_respond_lines) == 0, "Empty respond should not render standalone prefix"
    assert "Found 10 items" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_whitespace_only_respond_suppressed(capsys, mock_config):
    """Whitespace-only respond events should not render prefix."""
    events = [
        {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'},
        {"type": "execute"},
        {"type": "result", "payload": {"outcome": "Listed 10 items"}},
        {"type": "respond", "content": " \n"},
        {"type": "respond", "content": "Found 10 items"},
        {"type": "end"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    out_lines = [line for line in captured.out.split("\n") if line.strip()]

    empty_respond_lines = [line for line in out_lines if line.strip() == f"{C.MAGENTA}›{C.R}"]
    assert len(empty_respond_lines) == 0, (
        "Whitespace-only respond should not render standalone prefix"
    )
    assert "Found 10 items" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_trailing_whitespace_cleared_before_tool(capsys, mock_config):
    """Trailing whitespace after respond should be cleared before next tool."""
    events = [
        {"type": "respond", "content": "Checking files"},
        {"type": "respond", "content": "\n\n"},
        {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'},
        {"type": "execute"},
        {"type": "result", "payload": {"outcome": "Listed 10 items"}},
        {"type": "end"},
    ]
    stream = generate_events(events)
    renderer = Renderer(config=mock_config)

    await renderer.render_stream(stream)

    captured = capsys.readouterr()
    # Should not have excessive blank lines between "Checking files" and tool call
    assert "\n\n\n\n" not in captured.out
    assert "Checking files" in captured.out
    assert "10 items" in captured.out
