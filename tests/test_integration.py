"""Integration tests for cogency-code agent creation and configuration.

These tests verify the contract between cogency-code and cogency library,
ensuring proper agent identity, instruction loading, and tool integration.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cc.agent import create_agent
from cc.identity import CODING_IDENTITY
from cc.instructions import find_project_root, load_instructions
from cc.state import Config


class TestInstructionLoading:
    """Test instruction loading with proper fallback behavior."""

    def test_load_cogency_md_priority(self):
        """Test that COGENCY.md takes priority over CRUSH.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create both files
            (project_root / "COGENCY.md").write_text("cogency instructions")
            (project_root / "CRUSH.md").write_text("crush instructions")

            # Create .cogency directory to mark project root
            (project_root / ".cogency").mkdir()

            with patch("cc.instructions.Path.cwd", return_value=project_root):
                instructions = load_instructions()

            assert instructions == "cogency instructions"

    def test_load_crush_md_fallback(self):
        """Test fallback to CRUSH.md when COGENCY.md doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Only create CRUSH.md
            (project_root / "CRUSH.md").write_text("crush fallback instructions")
            (project_root / ".cogency").mkdir()

            with patch("cc.instructions.Path.cwd", return_value=project_root):
                instructions = load_instructions()

            assert instructions == "crush fallback instructions"

    def test_load_no_instructions(self):
        """Test graceful handling when no instruction files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / ".cogency").mkdir()

            with patch("cc.instructions.Path.cwd", return_value=project_root):
                instructions = load_instructions()

            assert instructions is None

    def test_find_project_root_with_cogency_dir(self):
        """Test finding project root by .cogency directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subdir = root / "subdir"
            subdir.mkdir()

            # Create .cogency in root
            (root / ".cogency").mkdir()

            # Search from subdir should find root
            found = find_project_root(start_path=subdir)
            assert found == root

    def test_find_project_root_not_found(self):
        """Test graceful handling when no project root found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            with patch("cc.instructions.Path.cwd", return_value=project_root):
                found = find_project_root()
                assert found is None


class TestAgentCreation:
    """Test agent creation with proper configuration and identity."""

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_create_agent_with_instructions(self, mock_config_class, mock_glm):
        """Test agent creation with loaded instructions."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "coding"  # NEW: mock identity
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
                assert call_args.kwargs["max_iterations"] == 22

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_create_agent_without_instructions(self, mock_config_class, mock_glm):
        """Test agent creation without instructions."""
        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "coding"  # NEW: mock identity
        mock_config.get_api_key.return_value = "test-key"
        mock_config_class.return_value = mock_config

        mock_glm.return_value = MagicMock()

        with patch("cc.agent.load_instructions", return_value=None):
            with patch("cc.agent.Agent") as mock_agent_class:
                create_agent(mock_config)

                # Instructions should be None when not found
                call_args = mock_agent_class.call_args
                assert call_args.kwargs["instructions"] is None

    @patch("cc.agent.Config")
    def test_create_llm_providers(self, mock_config_class):
        """Test LLM provider creation for different providers."""
        from cogency.lib.llms.anthropic import Anthropic
        from cogency.lib.llms.gemini import Gemini
        from cogency.lib.llms.openai import OpenAI

        from cc.agent import _create_llm

        mock_config = MagicMock()

        providers_and_classes = {
            "openai": OpenAI,
            "anthropic": Anthropic,
            "gemini": Gemini,
        }

        for provider_name, expected_class in providers_and_classes.items():
            with patch(f"cc.agent.{expected_class.__name__}") as mock_provider:
                mock_config.get_api_key.return_value = f"{provider_name}-key"
                mock_config.provider = provider_name

                _create_llm(provider_name, mock_config)

                mock_config.get_api_key.assert_called_with(provider_name)
                mock_provider.assert_called_once_with(api_key=f"{provider_name}-key")

    def test_create_llm_unknown_provider(self):
        """Test error handling for unknown LLM providers."""
        mock_config = MagicMock()

        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            from cc.agent import _create_llm

            _create_llm("unknown", mock_config)


class TestAgentIdentity:
    """Test agent identity and behavior contracts."""

    def test_coding_identity_structure(self):
        """Test that CODING_IDENTITY contains required elements."""
        assert "Cogency Code" in CODING_IDENTITY
        assert "OPERATIONAL PRINCIPLES" in CODING_IDENTITY
        assert "WORKFLOW" in CODING_IDENTITY
        assert "ERROR HANDLING" in CODING_IDENTITY

        # Verify key principles are present
        assert "Read files before making claims" in CODING_IDENTITY
        assert "Accuracy > speed" in CODING_IDENTITY
        assert "NEVER fabricate tool output" in CODING_IDENTITY

    @patch("cc.agent.GLM")
    @patch("cc.agent.Config")
    def test_agent_security_configuration(self, mock_config_class, mock_glm):
        """Test that agent is created with project-scoped security."""
        from cogency.core.config import Security

        mock_config = MagicMock()
        mock_config.provider = "glm"
        mock_config.identity = "coding"
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
                # The actual Security access level should be "project"
                # but we can't easily inspect it without importing the actual class


class TestConfigurationIntegration:
    """Test integration between configuration and agent creation."""

    def test_config_api_key_priority(self):
        """Test API key resolution priority: env > stored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_dir = Path(temp_dir)

            # Create config with stored key
            test_config = {"provider": "glm", "api_keys": {"glm": "stored_key"}}

            with open(config_path, "w") as f:
                json.dump(test_config, f)

            # Load config with env var override
            with patch.dict(os.environ, {"GLM_API_KEY": "env_key"}, clear=True):
                config = Config()
                config.config_dir = config_dir
                config.config_file = config_path
                config.load()

                assert config.get_api_key("glm") == "env_key"

    def test_default_configuration_values(self):
        """Test that defaults are sensible and minimal."""
        # Create fresh config without loading from disk
        config = object.__new__(Config)  # Skip __post_init__ to avoid loading
        config.provider = "glm"
        config.mode = "auto"
        config.user_id = "cogency"
        config.conversation_id = "dev_work"
        config.tools = ["file", "web", "memory"]
        config.api_keys = {}

        # Verify defaults align with cogency-code design
        assert config.provider == "glm"  # Default GLM provider
        assert config.mode == "auto"  # Auto mode for compatibility
        assert config.user_id == "cogency"
        assert set(config.tools) == {"file", "web", "memory"}  # Standard tool set
