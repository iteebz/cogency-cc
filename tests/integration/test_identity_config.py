"""Tests for identity configurability."""

from unittest.mock import MagicMock, patch

from cc.agent import create_agent


class TestIdentityConfiguration:
    """Test agent identity configurability."""

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_agent_with_coding_identity(self, mock_config_class, mock_glm):
        """Test agent creation with coding identity."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "coding"
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cc.agent.load_instructions", return_value=None):
            with patch("cc.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                call_args = mock_agent_class.call_args
                identity = call_args.kwargs["identity"]

                assert "Cogency Code" in identity
                assert "coding agent" in identity

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_agent_with_cothinker_identity(self, mock_config_class, mock_glm):
        """Test agent creation with cothinker identity."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "cothinker"
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cc.agent.load_instructions", return_value=None):
            with patch("cc.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                call_args = mock_agent_class.call_args
                identity = call_args.kwargs["identity"]

                assert "Cothinker" in identity
                assert "critical thinking partner" in identity

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_agent_with_assistant_identity(self, mock_config_class, mock_glm):
        """Test agent creation with assistant identity."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "assistant"
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cc.agent.load_instructions", return_value=None):
            with patch("cc.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                call_args = mock_agent_class.call_args
                identity = call_args.kwargs["identity"]

                assert "helpful assistant" in identity
                assert "accommodating and supportive" in identity