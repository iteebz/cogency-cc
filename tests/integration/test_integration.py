"""Integration tests for cogency-cc agent creation and configuration.

These tests verify the contract between cogency-cc and cogency library,
ensuring proper agent identity, instruction loading, and tool integration.
"""

from unittest.mock import MagicMock, patch

from cc.agent import create_agent


class TestAgentCreation:
    """Test agent creation with proper configuration and identity."""

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_with_instructions(self, mock_config_class, mock_glm):
        """Test agent creation with loaded instructions."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "code"  # NEW: mock identity
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        # Mock instruction loading
        with patch("cc.agent.load_instructions", return_value="Custom instructions"):
            with patch("cc.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                # Verify agent was created with correct parameters
                mock_agent_class.assert_called_once()
                call_args = mock_agent_class.call_args

                assert "Custom instructions" in call_args.kwargs["instructions"]
                assert call_args.kwargs["max_iterations"] == 42

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_without_instructions(self, mock_config_class, mock_glm):
        """Test agent creation without instructions."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "code"  # NEW: mock identity
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cc.agent.load_instructions", return_value=None):
            with patch("cc.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                # Instructions should be None when not found
                call_args = mock_agent_class.call_args
                assert call_args.kwargs["instructions"] is None


class TestAgentIdentity:
    """Test agent identity and behavior contracts."""

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_security_configuration(self, mock_config_class, mock_glm):
        """Test that agent is created with project-scoped security."""
        from cogency.core.config import Security

        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "code"
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config
        mock_glm.return_value = MagicMock()

        with patch("cc.agent.load_instructions", return_value=None):
            with patch("cc.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                # Verify security configuration
                call_args = mock_agent_class.call_args
                security = call_args.kwargs["security"]
                assert isinstance(security, Security)
