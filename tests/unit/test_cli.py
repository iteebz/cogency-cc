"""Test CLI argument parsing and routing for the core 'run' command."""

from unittest.mock import MagicMock, patch

from typer.main import get_command
from typer.testing import CliRunner

from cc.__main__ import main as cli


def test_run_without_args_shows_help():
    """Contract: Test that running 'run' without a query shows help and exits."""
    runner = CliRunner()
    result = runner.invoke(get_command(cli), ["run"])
    assert result.exit_code == 0
    assert "Usage: cli" in result.output


@patch("cc.__main__.run_agent")
def test_run_with_query_invokes_agent(mock_run_agent):
    """Core Behavior: Test that a simple query correctly invokes the agent runner."""
    runner = CliRunner()
    result = runner.invoke(get_command(cli), ["run", "hello world"])
    assert result.exit_code == 0

    mock_run_agent.assert_called_once()
    args, kwargs = mock_run_agent.call_args
    assert args[1] == "hello world"  # query


@patch("cc.__main__.run_agent")
def test_run_new_flag_is_passed(mock_run_agent):
    """Contract: Test that the --new flag is correctly passed to the agent runner."""
    runner = CliRunner()
    runner.invoke(get_command(cli), ["run", "--new", "test query"])

    args, kwargs = mock_run_agent.call_args
    assert args[3] is False  # resuming should be False


@patch("cc.agent.create_agent")
def test_run_model_aliases_configure_agent(mock_create_agent):
    """Contract: Test that model alias flags correctly configure the agent provider and model."""
    test_cases = [
        (["run", "--model-alias", "codex", "test"], "openai", "gpt-5-codex", "Codex"),
        (["run", "--model-alias", "gemini", "test"], "gemini", "gemini-2.5-pro", "Gemini"),
        (["run", "--model-alias", "sonnet", "test"], "anthropic", "claude-sonnet-4-5", "Claude"),
        (
            ["run", "--model-alias", "gemini-live", "test"],
            "gemini",
            "gemini-1.5-flash-latest",
            "Gemini",
        ),
    ]

    for args, expected_provider, expected_model, _expected_identity_name in test_cases:
        mock_create_agent.reset_mock()
        runner = CliRunner()
        runner.invoke(get_command(cli), args)

        mock_create_agent.assert_called_once()
        config_arg = mock_create_agent.call_args[0][0]  # First arg is the config object
        assert config_arg.provider == expected_provider
        assert config_arg.model == expected_model

        # Mock the returned agent to prevent errors in run_agent
        mock_agent_instance = MagicMock()
        mock_agent_instance.config.llm.http_model = expected_model
        mock_create_agent.return_value = mock_agent_instance


@patch("asyncio.run")
def test_run_conv_flag_is_passed(mock_asyncio_run):
    """Contract: Test --conv flag sets the conversation ID."""
    mock_run_agent_func = MagicMock()
    mock_run_agent_coroutine_result = MagicMock()
    mock_run_agent_func.return_value = mock_run_agent_coroutine_result

    with patch("cc.__main__.run_agent", new=mock_run_agent_func):
        runner = CliRunner()
        runner.invoke(get_command(cli), ["run", "--conv", "test-conv-id", "query"])

    mock_asyncio_run.assert_called_once_with(mock_run_agent_coroutine_result)
    mock_run_agent_func.assert_called_once()
    args, kwargs = mock_run_agent_func.call_args
    assert args[2] == "test-conv-id"  # conv_id
