import uuid
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from cc.cli import app as cli


def test_no_args_shows_help():
    """Contract: Running without a query should show help and exit with error."""
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 2
    assert "Usage: root" in result.output


@patch("cc.cli.run_agent")
def test_query_invokes_agent(mock_run_agent):
    """Core Behavior: A simple query invokes the agent runner."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hello", "world"])
    assert result.exit_code == 0

    mock_run_agent.assert_called_once()
    args, kwargs = mock_run_agent.call_args
    assert args[1] == "hello world"  # query


@patch("cc.cli.run_agent")
def test_literal_run_is_treated_as_query(mock_run_agent):
    """Regression: The word 'run' should be treated as part of the query, not a subcommand."""
    runner = CliRunner()
    runner.invoke(cli, ["run", "hello"])

    mock_run_agent.assert_called_once()
    args, kwargs = mock_run_agent.call_args
    assert args[1] == "run hello"


@patch("cc.cli.run_agent")
def test_run_new_flag_is_passed(mock_run_agent):
    """Contract: Test that the --new flag is correctly passed to the agent runner."""
    runner = CliRunner()
    runner.invoke(cli, ["--new", "test query"])

    args, kwargs = mock_run_agent.call_args
    assert args[3] is False  # resuming should be False


@patch("cc.cli.run_agent")
@patch("cc.cli.uuid.uuid4")
def test_run_new_generates_fresh_conversation(mock_uuid, mock_run_agent):
    """Behavior: --new generates a fresh conversation ID and updates config."""
    mock_uuid.return_value = uuid.UUID("12345678-1234-1234-1234-1234567890ab")
    runner = CliRunner()
    runner.invoke(cli, ["--new", "fresh start"])

    args, kwargs = mock_run_agent.call_args
    assert args[2] == str(mock_uuid.return_value)
    config_arg = args[5]
    assert config_arg.conversation_id == str(mock_uuid.return_value)


@patch("cc.cli.create_agent")
def test_run_model_aliases_configure_agent(mock_create_agent):
    """Contract: Test that model alias flags correctly configure the agent provider and model."""
    test_cases = [
        (["--model-alias", "gemini", "test"], "gemini", "gemini-2.5-pro", "Gemini"),
        (["--model-alias", "sonnet", "test"], "anthropic", "claude-sonnet-4-5", "Claude"),
        (
            ["--model-alias", "gemini-live", "test"],
            "gemini",
            "gemini-1.5-flash-latest",
            "Gemini",
        ),
    ]

    for args, expected_provider, expected_model, _expected_identity_name in test_cases:
        mock_create_agent.reset_mock()
        runner = CliRunner()
        runner.invoke(cli, args)

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

    with patch("cc.cli.run_agent", new=mock_run_agent_func):
        runner = CliRunner()
        runner.invoke(cli, ["--conv", "test-conv-id", "query"])

    mock_asyncio_run.assert_called_once_with(mock_run_agent_coroutine_result)
    mock_run_agent_func.assert_called_once()
    args, kwargs = mock_run_agent_func.call_args
    assert args[2] == "test-conv-id"  # conv_id
