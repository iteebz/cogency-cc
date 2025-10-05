"""Tests for identity configurability."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cogency_code.agent import create_agent
from cogency_code.identity import get_identity, list_identity
from cogency_code.state import Config


class TestIdentityConfiguration:
    """Test agent identity configurability."""

    def test_list_identity(self):
        """Test listing available identities."""
        identity = list_identity()
        expected = ["coding", "cothinker", "assistant"]
        assert identity == expected

    def test_get_identity_coding(self):
        """Test getting coding identity."""
        identity = get_identity("coding")
        assert "Cogency Code" in identity
        assert "coding agent" in identity
        assert "read, write, and reason about code" in identity

    def test_get_identity_cothinker(self):
        """Test getting cothinker identity."""
        identity = get_identity("cothinker")
        assert "Cothinker" in identity
        assert "critical thinking partner" in identity
        assert "prevent bad implementations" in identity

    def test_get_identity_assistant(self):
        """Test getting assistant identity."""
        identity = get_identity("assistant")
        assert "helpful assistant" in identity
        assert "accommodating and supportive" in identity

    def test_get_identity_unknown(self):
        """Test error for unknown identity."""
        with pytest.raises(ValueError, match="Unknown identity 'unknown'"):
            get_identity("unknown")

    @patch("cogency_code.agent.GLM")
    @patch("cogency_code.agent.Config")
    def test_agent_with_coding_identity(self, mock_config_class, mock_glm):
        """Test agent creation with coding identity."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "coding"
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cogency_code.agent.load_instructions", return_value=None):
            with patch("cogency_code.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                call_args = mock_agent_class.call_args
                identity = call_args.kwargs["identity"]

                assert "Cogency Code" in identity
                assert "coding agent" in identity

    @patch("cogency_code.agent.GLM")
    @patch("cogency_code.agent.Config")
    def test_agent_with_cothinker_identity(self, mock_config_class, mock_glm):
        """Test agent creation with cothinker identity."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "cothinker"
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cogency_code.agent.load_instructions", return_value=None):
            with patch("cogency_code.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                call_args = mock_agent_class.call_args
                identity = call_args.kwargs["identity"]

                assert "Cothinker" in identity
                assert "critical thinking partner" in identity

    @patch("cogency_code.agent.GLM")
    @patch("cogency_code.agent.Config")
    def test_agent_with_assistant_identity(self, mock_config_class, mock_glm):
        """Test agent creation with assistant identity."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "assistant"
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cogency_code.agent.load_instructions", return_value=None):
            with patch("cogency_code.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                call_args = mock_agent_class.call_args
                identity = call_args.kwargs["identity"]

                assert "helpful assistant" in identity
                assert "accommodating and supportive" in identity

    def test_config_default_identity(self):
        """Test config has default identity."""
        config = Config()
        assert config.identity == "coding"

    def test_config_identity_persistence(self, tmp_path):
        """Test identity persists to config file."""
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            config = Config()
            config.config_dir = Path(temp_dir)
            config.config_file = config_file
            config.identity = "cothinker"
            config.save()

            # Load and verify
            with open(config_file) as f:
                data = json.load(f)

            assert data["identity"] == "cothinker"
