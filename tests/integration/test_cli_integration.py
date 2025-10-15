"""Integration tests for the cc CLI."""

import os
import stat
from unittest.mock import patch

from typer.testing import CliRunner

from cc.cli import app
from tests.conftest import MockLLM


@patch("cc.agent._create_llm")
def test_run_in_non_writable_directory_fails_gracefully(mock_create_llm, cli_runner: CliRunner):
    """Test that the CLI exits gracefully when run from a non-writable directory."""
    mock_create_llm.return_value = MockLLM()

    with cli_runner.isolated_filesystem() as temp_dir:
        non_writable_dir_path = os.path.join(temp_dir, "non_writable")
        os.makedirs(non_writable_dir_path)

        # Make the directory non-writable for the owner
        os.chmod(non_writable_dir_path, stat.S_IREAD | stat.S_IEXEC)

        original_cwd = os.getcwd()
        try:
            os.chdir(non_writable_dir_path)
            result = cli_runner.invoke(app, ["hello world"])

            assert result.exit_code == 1, (
                f"Expected exit code 1, but got {result.exit_code}. Output:\n{result.stdout}"
            )
            assert isinstance(result.exception, SystemExit)
            assert (
                "Error: Cannot create or open database in the current directory." in result.stdout
            )
            assert "Please run from a directory where you have write permissions." in result.stdout

        finally:
            # Restore permissions to allow cleanup by the context manager
            os.chmod(non_writable_dir_path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
            os.chdir(original_cwd)
