"""Test CLI argument parsing and routing."""

import sys
from unittest.mock import patch

import pytest

from cc.__main__ import main


def test_no_args_exits_with_usage():
    """Test that running without arguments shows usage and exits."""
    with patch.object(sys, "argv", ["cc"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


@patch("cc.__main__.run")
def test_basic_query_execution(mock_run):
    """Test basic query execution."""
    with patch.object(sys, "argv", ["cc", "hello world"]):
        main()

    mock_run.assert_called_once()
    args = mock_run.call_args[0]
    assert args[0] is not None  # agent
    assert args[1] == "hello world"  # query
    assert args[2] is not None  # conv_id


@patch("cc.__main__.run")
def test_new_flag_forces_new_conversation(mock_run):
    """Test that --new flag forces a new conversation."""
    with patch.object(sys, "argv", ["cc", "--new", "test query"]):
        main()

    args = mock_run.call_args[0]
    assert args[3] is False  # resuming should be False


@patch("cc.__main__.create_agent")
@patch("cc.__main__.run")
def test_model_aliases(mock_run, mock_create_agent):
    """Test model alias flags."""
    test_cases = [
        (["cc", "--glm", "test"], "glm"),
        (["cc", "--claude", "test"], "anthropic"),
        (["cc", "--gemini", "test"], "gemini"),
        (["cc", "--codex", "test"], "openai"),
        (["cc", "--gpt41", "test"], "openai"),
    ]

    for argv, expected_provider in test_cases:
        mock_run.reset_mock()
        mock_create_agent.reset_mock()

        with patch.object(sys, "argv", argv):
            main()

        # Check that create_agent was called with correct config
        mock_create_agent.assert_called_once()
        config_arg = mock_create_agent.call_args[0][0]
        assert config_arg.provider == expected_provider


def test_debug_flag_enables_debug_logging():
    """Test that --debug flag enables debug logging."""
    with (
        patch.object(sys, "argv", ["cc", "--debug", "test"]),
        patch("cc.__main__.run"),
        patch("cogency.lib.logger.set_debug") as mock_debug,
    ):
        main()

    mock_debug.assert_called_once_with(True)


def test_profile_flag_shows_profile(tmp_path):
    """Test --profile flag displays profile information."""
    # Create a mock profile file
    cogency_dir = tmp_path / ".cogency"
    cogency_dir.mkdir()
    profile_file = cogency_dir / "profile.json"
    profile_file.write_text('{"name": "test", "version": "1.0"}')

    with (
        patch.object(sys, "argv", ["cc", "--profile"]),
        patch("pathlib.Path.cwd", return_value=tmp_path),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 0


def test_profile_flag_no_profile_file(tmp_path):
    """Test --profile flag when no profile exists."""
    with (
        patch.object(sys, "argv", ["cc", "--profile"]),
        patch("pathlib.Path.cwd", return_value=tmp_path),
        pytest.raises(SystemExit) as exc_info,
        patch("builtins.print") as mock_print,
    ):
        main()

    assert exc_info.value.code == 0
    mock_print.assert_called_with("No profile found")


def test_nuke_flag_deletes_cogency_dir(tmp_path):
    """Test --nuke flag deletes .cogency directory."""
    # Create a mock .cogency directory
    cogency_dir = tmp_path / ".cogency"
    cogency_dir.mkdir()

    with (
        patch.object(sys, "argv", ["cc", "--nuke"]),
        patch("cc.__main__.find_project_root", return_value=tmp_path),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 0
    assert not cogency_dir.exists()


@patch("cc.__main__.show_context")
def test_context_flag_calls_show_context(mock_show):
    """Test --context flag calls show_context."""
    with patch.object(sys, "argv", ["cc", "--context"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    mock_show.assert_called_once()


@patch("cc.summary.show_summary")
def test_summary_flag_calls_show_summary(mock_show):
    """Test --summary flag calls show_summary."""
    with patch.object(sys, "argv", ["cc", "--summary"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    mock_show.assert_called_once()


@patch("cc.compact.compact_context")
def test_compact_flag_calls_compact_context(mock_compact):
    """Test --compact flag calls compact_context."""
    with patch.object(sys, "argv", ["cc", "--compact"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    mock_compact.assert_called_once()


def test_conv_flag_sets_conversation_id():
    """Test --conv flag sets specific conversation ID."""
    with (
        patch.object(sys, "argv", ["cc", "--conv", "test-conv-id", "query"]),
        patch("cc.__main__.run") as mock_run,
    ):
        main()

    args = mock_run.call_args[0]
    assert args[2] == "test-conv-id"  # conv_id


def test_evo_flag_enables_evo_mode():
    """Test --evo flag enables evolution mode."""
    with (
        patch.object(sys, "argv", ["cc", "--evo", "test query"]),
        patch("cc.__main__.run") as mock_run,
    ):
        main()

    args = mock_run.call_args[0]
    assert args[4] is True  # evo_mode


def test_conv_flag_without_id_exits():
    """Test --conv flag without ID should exit gracefully."""
    with patch.object(sys, "argv", ["cc", "--conv"]), patch("cc.__main__.run") as mock_run:
        # Should not crash when --conv has no argument
        main()

    mock_run.assert_called_once()


def test_multiple_flags_combination():
    """Test multiple flags work together."""
    with (
        patch.object(sys, "argv", ["cc", "--debug", "--new", "--evo", "test query"]),
        patch("cc.__main__.run") as mock_run,
        patch("cogency.lib.logger.set_debug") as mock_debug,
    ):
        main()

    mock_debug.assert_called_once_with(True)
    args = mock_run.call_args[0]
    assert args[3] is False  # resuming (due to --new)
    assert args[4] is True  # evo_mode
