"""Test auxiliary CLI commands."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from cc.cli import app as cli


@patch("cc.commands.show_profile", new_callable=AsyncMock)
def test_profile_command_shows_profile(mock_show_profile):
    """Test that the 'profile' command calls the correct handler."""
    runner = CliRunner()
    result = runner.invoke(cli, ["profile"])
    assert result.exit_code == 0
    mock_show_profile.assert_called_once()


@patch("shutil.rmtree")
@patch("cc.lib.fs.root")
def test_nuke_command_deletes_cogency_dir(mock_find_root, mock_rmtree):
    """Test that the 'nuke' command calls the correct file system operations."""
    # Mock root to return a valid path, so the command proceeds
    mock_find_root.return_value = MagicMock()
    mock_find_root.return_value.exists.return_value = True
    mock_find_root.return_value.is_dir.return_value = True

    runner = CliRunner()
    # Simulate user confirming the action
    result = runner.invoke(cli, ["nuke"], input="y\n")

    assert result.exit_code == 0
    mock_rmtree.assert_called_once()


@patch("cc.commands.show_context", new_callable=AsyncMock)
def test_context_command_calls_show_context(mock_show_context):
    """Test that the 'context' command calls the correct handler."""
    runner = CliRunner()
    result = runner.invoke(cli, ["context"])
    assert result.exit_code == 0
    mock_show_context.assert_called_once()
