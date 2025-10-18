"""Unit tests for incremental buffer flushing."""

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


def test_buffer_delimiter_flush_stops_at_delimiter():
    """Flush stops at delimiter and keeps remainder in buffer."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("para1\n\npara2\n\npara3")
    buffer.flush_incremental(mock_printer, delimiter="\n\n")

    assert len(output) == 2
    assert output[0] == "para1"
    assert output[1] == "\n\n"

    buffer.flush_incremental(mock_printer, delimiter="\n\n")
    assert len(output) == 4
    assert output[2] == "para2"
    assert output[3] == "\n\n"


def test_buffer_delimiter_trims_trailing_whitespace():
    """Trailing whitespace trimmed from flushed chunk."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("text with spaces   \n\nnext")
    buffer.flush_incremental(mock_printer, delimiter="\n\n")

    assert output[0] == "text with spaces"
    assert output[1] == "\n\n"


def test_buffer_delimiter_no_delimiter_flushes_all():
    """If no delimiter found, flush all accumulated content."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("no delimiter here")
    buffer.flush_incremental(mock_printer, delimiter="\n\n")

    assert len(output) == 1
    assert output[0] == "no delimiter here"


def test_buffer_delimiter_empty_after_delimiter():
    """Only delimiter remains - no output, remainder is empty."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("text\n\n")
    buffer.flush_incremental(mock_printer, delimiter="\n\n")

    assert len(output) == 2
    assert output[0] == "text"
    assert output[1] == "\n\n"


def test_buffer_delimiter_trailing_newlines_rstripped():
    """Rstrip removes trailing whitespace including embedded newlines."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("line1\nline2\n\nnext")
    buffer.flush_incremental(mock_printer, delimiter="\n\n")

    result = output[0]
    assert result == "line1\nline2"


def test_buffer_delimiter_with_tabs_and_spaces():
    """Tabs and spaces trimmed from trailing whitespace."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("text\t  \n\nnext")
    buffer.flush_incremental(mock_printer, delimiter="\n\n")

    assert output[0] == "text"


def test_buffer_leading_whitespace_stripped_immediately():
    """Leading whitespace stripped immediately after delimiter detected."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("text\n\n  \n  \nreal content")
    buffer.flush_incremental(mock_printer, delimiter="\n\n", buffer_leading_ws=True)

    assert len(output) == 2
    assert output[0] == "text"
    assert output[1] == "\n\n"
    assert not buffer.empty

    delim_end = 6
    ws_to_strip = "  \n  \n"
    expected_flushed_after_first = delim_end + len(ws_to_strip)
    assert buffer._flushed_len == expected_flushed_after_first

    buffer.flush_incremental(mock_printer, delimiter="\n\n", buffer_leading_ws=True)
    assert len(output) == 3
    assert output[2] == "real content"


def test_buffer_internal_newlines_preserved_if_content():
    """Internal newlines preserved if real content follows."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("line1\n\nline2\n\nmore")
    buffer.flush_incremental(mock_printer, delimiter="\n\n", buffer_leading_ws=True)

    assert output[0] == "line1"
    assert output[1] == "\n\n"

    buffer.flush_incremental(mock_printer, delimiter="\n\n", buffer_leading_ws=True)
    assert output[2] == "line2"
    assert output[3] == "\n\n"


def test_buffer_trailing_newlines_discarded_on_delimiter():
    """Trailing newlines discarded when next delimiter found."""
    buffer = Buffer()
    output = []

    def mock_printer(text, end=""):
        output.append(text)

    buffer.append("para1\n\npara2\n\npara3")
    buffer.flush_incremental(mock_printer, delimiter="\n\n", buffer_leading_ws=True)
    assert output[0] == "para1"
    assert output[1] == "\n\n"

    buffer.flush_incremental(mock_printer, delimiter="\n\n", buffer_leading_ws=True)
    assert output[2] == "para2"
    assert output[3] == "\n\n"

    buffer.flush_incremental(mock_printer, delimiter="\n\n", buffer_leading_ws=True)
    assert output[4] == "para3"
    assert len(output) == 5
