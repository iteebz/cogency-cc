"""Tests for agent creation and configuration."""

from unittest.mock import MagicMock, patch

from cc.agent import create_agent


@patch("cc.agent.GLM")
@patch("cc.agent.Config")
def test_with_instructions(mock_config_class, mock_glm):
    """Test agent creation with loaded instructions."""
    # Setup mocks
    mock_config = MagicMock()
    mock_config.provider = "glm"
    mock_config.identity = "code"
    mock_config.get_api_key.return_value = "test-key"
    mock_config_class.return_value = mock_config

    mock_glm.return_value = MagicMock()

    # Mock instruction loading
    with patch(
        "cc.cc_md.load",
        return_value="--- User .cogency/cc.md ---\nCustom instructions\n--- End .cogency/cc.md ---",
    ):
        with patch("cc.agent.Agent") as mock_agent_class:
            create_agent(mock_config)

            # Verify agent was created with correct parameters
            mock_agent_class.assert_called_once()
            call_args = mock_agent_class.call_args

            assert "Custom instructions" in call_args.kwargs["instructions"]
            assert "You are cogency coding cli (cc)" in call_args.kwargs["identity"]
            assert call_args.kwargs["max_iterations"] == 42


@patch("cc.agent.GLM")
@patch("cc.agent.Config")
def test_without_instructions(mock_config_class, mock_glm):
    """Test agent creation without instructions."""
    mock_config = MagicMock()
    mock_config.provider = "glm"
    mock_config.identity = "code"
    mock_config.get_api_key.return_value = "test-key"
    mock_config_class.return_value = mock_config

    mock_glm.return_value = MagicMock()

    with patch("cc.cc_md.load", return_value=None):
        with patch("cc.agent.Agent") as mock_agent_class:
            create_agent(mock_config)

            # Instructions should be empty when not found
            call_args = mock_agent_class.call_args
            assert call_args.kwargs["instructions"] == ""
            assert "You are cogency coding cli (cc)" in call_args.kwargs["identity"]
