"""Test boundary trimming contracts for think/respond chunks."""

from unittest.mock import MagicMock, patch

import pytest

from cc.render import Renderer
from cc.render.color import C


async def gen_events(events):
    for event in events:
        yield event


@pytest.fixture
def cfg():
    c = MagicMock()
    c.model = "test-model"
    return c


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_trailing_newlines_buffered_not_printed(capsys, cfg):
    """Trailing newlines in respond chunks buffered, not immediately printed."""
    events = [
        {"type": "respond", "content": "Response"},
        {"type": "respond", "content": "\n\n\n"},
        {"type": "respond", "content": "Continued"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert "Response" in captured.out
    assert "Continued" in captured.out
    assert captured.out.count("\n\n\n\n") == 0


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_trailing_newlines_not_flushed_before_delimiter(capsys, cfg):
    """Trailing newlines before tool call not rendered."""
    events = [
        {"type": "respond", "content": "Analyzing"},
        {"type": "respond", "content": "\n\n"},
        {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'},
        {"type": "result", "payload": {"outcome": "Listed"}},
        {"type": "end"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert "Analyzing" in captured.out
    assert "\n\n\n\n" not in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_leading_newlines_stripped_on_transition(capsys, cfg):
    """Leading newlines stripped at think/respond mode entry."""
    events = [
        {"type": "think", "content": "\n\n\nActual thought"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert f"{C.GRAY}~{C.R} {C.GRAY}Actual thought{C.R}" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_respond_leading_newlines_stripped_on_transition(capsys, cfg):
    """Leading newlines stripped at respond mode entry."""
    events = [
        {"type": "respond", "content": "\n\nActual response"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert f"{C.MAGENTA}›{C.R} Actual response" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_internal_newlines_preserved(capsys, cfg):
    """Internal newlines within chunks preserved."""
    events = [
        {"type": "respond", "content": "Line1\n\nLine2\n\nLine3"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert "Line1\n\nLine2\n\nLine3" in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_think_trailing_newlines_buffered(capsys, cfg):
    """Trailing newlines in think chunks buffered."""
    events = [
        {"type": "think", "content": "Thinking"},
        {"type": "think", "content": "\n\n"},
        {"type": "respond", "content": "Response"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert "Thinking" in captured.out
    assert "Response" in captured.out
    assert captured.out.count("\n\n\n\n") == 0


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_trailing_whitespace_before_tool_cleared(capsys, cfg):
    """Trailing whitespace before tool call doesn't create excess blank lines."""
    events = [
        {"type": "respond", "content": "Check files"},
        {"type": "respond", "content": "  \n  \n  "},
        {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'},
        {"type": "result", "payload": {"outcome": "OK"}},
        {"type": "end"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert "Check files" in captured.out
    assert "○" in captured.out
    assert "\n\n\n\n" not in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_multiple_trailing_chunks_before_tool(capsys, cfg):
    """Multiple whitespace chunks before tool don't create spam."""
    events = [
        {"type": "respond", "content": "Starting"},
        {"type": "respond", "content": "\n"},
        {"type": "respond", "content": "\n"},
        {"type": "respond", "content": "  "},
        {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'},
        {"type": "result", "payload": {"outcome": "OK"}},
        {"type": "end"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert "Starting" in captured.out
    assert captured.out.count("\n\n\n\n") == 0


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_single_space_after_delimiter_respond(capsys, cfg):
    """Delimiter and content have exactly one space between."""
    events = [
        {"type": "respond", "content": "Test response"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert f"{C.MAGENTA}›{C.R} Test response" in captured.out
    assert f"{C.MAGENTA}›{C.R}  Test" not in captured.out


@pytest.mark.asyncio
@patch.dict("os.environ", {"CI": "true"})
async def test_single_space_after_delimiter_think(capsys, cfg):
    """Think delimiter and content have exactly one space between."""
    events = [
        {"type": "think", "content": "Thinking hard"},
    ]
    renderer = Renderer(config=cfg)
    await renderer.render_stream(gen_events(events))

    captured = capsys.readouterr()
    assert f"{C.GRAY}~{C.R} {C.GRAY}Thinking hard{C.R}" in captured.out
