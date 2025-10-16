"""Unit tests for incremental buffer flushing."""

import pytest

from cc.render.buffer import Buffer
from cc.render.color import C


def test_buffer_incremental_flush_plain_text():
    """Chunks flush immediately without markdown processing."""
    buffer = Buffer()
    output = []
    
    def mock_printer(text, end=""):
        output.append(text)
    
    buffer.append("Hello ")
    buffer.flush_incremental(mock_printer)
    
    buffer.append("world")
    buffer.flush_incremental(mock_printer)
    
    assert output == ["Hello ", "world"]
    assert "".join(output) == "Hello world"


def test_buffer_incremental_no_reprocess():
    """Already-flushed content is not reprocessed."""
    buffer = Buffer()
    output = []
    
    def mock_printer(text, end=""):
        output.append(text)
    
    buffer.append("chunk1")
    buffer.flush_incremental(mock_printer)
    assert len(output) == 1
    
    buffer.append("chunk2")
    buffer.flush_incremental(mock_printer)
    assert len(output) == 2
    assert output[1] == "chunk2"  # Only new chunk


def test_buffer_incremental_with_markdown():
    """Markdown formatting applies to flushed chunks."""
    buffer = Buffer()
    output = []
    
    def mock_printer(text, end=""):
        output.append(text)
    
    buffer.append("**bold** text")
    buffer.flush_incremental(mock_printer)
    
    result = "".join(output)
    assert f"{C.BOLD}bold{C.R}" in result
    assert "text" in result


def test_buffer_incremental_partial_markdown():
    """Markdown detection works within accumulated buffer."""
    buffer = Buffer()
    output = []
    
    def mock_printer(text, end=""):
        output.append(text)
    
    # Append chunks that together form markdown
    buffer.append("Here is `code`")
    buffer.flush_incremental(mock_printer)
    
    result = "".join(output)
    assert "Here is" in result
    # Code block detected in full accumulated string
    assert f"{C.GRAY}code{C.R}" in result


def test_buffer_incremental_newline_tracking():
    """Tracks whether output ends with newline."""
    buffer = Buffer()
    
    def mock_printer(text, end=""):
        pass
    
    result = buffer.flush_incremental(mock_printer)
    assert result is True  # Empty buffer ends with newline
    
    buffer.append("no newline")
    result = buffer.flush_incremental(mock_printer)
    assert result is False
    
    # Fresh buffer with newline
    buffer = Buffer()
    buffer.append("with newline\n")
    result = buffer.flush_incremental(mock_printer)
    assert result is True


def test_buffer_incremental_whitespace_only():
    """Whitespace-only chunks don't produce output but update tracking."""
    buffer = Buffer()
    output = []
    
    def mock_printer(text, end=""):
        output.append(text)
    
    buffer.append("   ")
    buffer.flush_incremental(mock_printer)
    
    assert len(output) == 0


def test_buffer_clear_resets_state():
    """Clear resets tracking for reuse."""
    buffer = Buffer()
    output = []
    
    def mock_printer(text, end=""):
        output.append(text)
    
    buffer.append("content")
    buffer.flush_incremental(mock_printer)
    
    buffer.clear()
    buffer.append("new content")
    buffer.flush_incremental(mock_printer)
    
    assert output[0] == "content"
    assert output[1] == "new content"


def test_buffer_backward_compat_flush_to():
    """Fallback flush_to still works for non-incremental code."""
    buffer = Buffer()
    output = []
    
    def mock_printer(text, end=""):
        output.append(text)
    
    buffer.append("chunk1")
    buffer.append("chunk2")
    buffer.flush_to(mock_printer)
    
    result = "".join(output)
    assert "chunk1chunk2" in result
    assert buffer.empty
