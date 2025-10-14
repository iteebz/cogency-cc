from unittest.mock import MagicMock, patch

from cc.tools.shell import shell


def test_shell_truncates_output():
    """Test that shell command truncates output when it exceeds max_lines."""
    # Create a mock that returns a long output
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "line\n" * 150  # 150 lines of output

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo 'test'")

        # The result should be truncated to max_lines (100)
        lines = result.split("\n")
        assert len(lines) <= 100
        assert "... (truncated)" in result


def test_shell_preserves_short_output():
    """Test that shell command doesn't truncate short output."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "line1\nline2\nline3"

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo 'test'")

        # The result should not be truncated
        lines = result.split("\n")
        assert len(lines) == 3
        assert "... (truncated)" not in result


def test_shell_handles_error_output():
    """Test that shell command properly handles error output."""
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stdout = "Success output"
    mock_process.stderr = "Error message"

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="invalid_command")

        # The result should include error information
        assert "Error message" in result
        assert "Command failed" in result


def test_shell_with_custom_max_lines():
    """Test that shell command respects custom max_lines parameter."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "line\n" * 50  # 50 lines of output

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo 'test'", max_lines=30)

        # The result should be truncated to custom max_lines
        lines = result.split("\n")
        assert len(lines) <= 30
        assert "... (truncated)" in result


def test_shell_with_empty_output():
    """Test that shell command handles empty output correctly."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ""

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo -n ''")

        # The result should be empty
        assert result == ""
