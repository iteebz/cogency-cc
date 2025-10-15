from unittest.mock import MagicMock, patch

from cc.tools.shell import shell


def test_shell_truncates_output():
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ("line\n" * 150).rstrip("\n")

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo 'test'")

        assert "(truncated" in result
        assert "showing first 100 of 150 lines" in result


def test_shell_preserves_short_output():
    """Test that shell command doesn't truncate short output."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "line1\nline2\nline3"

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo 'test'")

        lines = result.split("\n")
        assert len(lines) == 3
        assert "(truncated" not in result


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
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ("line\n" * 50).rstrip("\n")

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo 'test'", max_lines=30)

        assert "(truncated" in result
        assert "showing first 30 of 50 lines" in result


def test_shell_with_empty_output():
    """Test that shell command handles empty output correctly."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ""

    with patch("subprocess.run", return_value=mock_process):
        result = shell(command="echo -n ''")

        # The result should be empty
        assert result == ""
