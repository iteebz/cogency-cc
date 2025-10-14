"""Tests for shell output rendering."""


from cc.render.color import C
from cc.render.shell import _highlight_patterns, format_shell_output


def test_format_shell_output_success():
    """Test successful command output formatting."""
    content = "File created at /tmp/example.txt\nDone."
    result = format_shell_output(content, exit_code=0)

    assert C.GREEN in result
    assert C.CYAN in result  # File path should be highlighted
    assert C.R in result  # Reset code should be present


def test_format_shell_output_failure():
    """Test failed command output formatting."""
    content = "Error: File not found"
    result = format_shell_output(content, exit_code=1)

    assert C.RED in result
    assert C.R in result  # Reset code should be present


def test_highlight_patterns_file_paths():
    """Test file path highlighting."""
    line = "Created file at /home/user/example.txt"
    result = _highlight_patterns(line)

    assert C.CYAN in result
    assert "/home/user/example.txt" in result


def test_highlight_patterns_urls():
    """Test URL highlighting."""
    line = "Download from https://example.com/file.zip"
    result = _highlight_patterns(line)

    assert C.BLUE in result
    assert "https://example.com/file.zip" in result


def test_highlight_patterns_errors():
    """Test error highlighting."""
    line = "ERROR: Failed to process file"
    result = _highlight_patterns(line)

    assert C.RED in result
    assert "ERROR: Failed to process file" in result


def test_highlight_patterns_warnings():
    """Test warning highlighting."""
    line = "WARNING: This is deprecated"
    result = _highlight_patterns(line)

    assert C.YELLOW in result
    assert "WARNING: This is deprecated" in result


def test_highlight_patterns_success():
    """Test success highlighting."""
    line = "Operation completed successfully"
    result = _highlight_patterns(line)

    assert C.GREEN in result
    assert "Operation completed successfully" in result


def test_empty_content():
    """Test handling of empty content."""
    result = format_shell_output("")
    assert result == ""


def test_multiline_content():
    """Test handling of multiline content."""
    content = "Line 1\nLine 2\nLine 3"
    result = format_shell_output(content)

    assert result.count("\n") == 2  # Should preserve line breaks
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result
