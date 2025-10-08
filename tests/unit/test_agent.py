"""Core agent behavior and contract tests."""

from unittest.mock import Mock, patch

import pytest

from cc.agent import _create_llm, _get_model_name, create_agent
from cc.state import Config


class TestAgentCreation:
    """Agent factory contract and behavior tests."""

    def test_create_agent_with_default_config(self):
        """Should create agent with expected defaults."""
        config = Mock(spec=Config)
        config.provider = "openai"
        config.model = "gpt-4"
        config.identity = "code"
        config.get_api_key.return_value = "test-key"

        with (
            patch("cogency.tools") as mock_tools,
            patch("cc.agent.load_instructions") as mock_instructions,
            patch("cc.agent.get_identity") as mock_identity,
        ):
            mock_tools.category.return_value = ["file_tool", "system_tool"]
            mock_instructions.return_value = "Help with coding"
            mock_identity.return_value = "You are a coding assistant"

            with (
                patch("cc.agent._create_llm") as mock_create_llm,
                patch("cc.agent.Agent") as mock_agent_class,
            ):
                mock_llm = Mock()
                mock_llm.http_model = "gpt-4"
                mock_create_llm.return_value = mock_llm

                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent

                create_agent(config)

                mock_agent_class.assert_called_once()
                call_kwargs = mock_agent_class.call_args[1]
                assert call_kwargs["max_iterations"] == 42
                assert call_kwargs["profile"] is True
                assert call_kwargs["mode"] == "auto"
                assert "gpt-4" in call_kwargs["identity"]

    def test_create_agent_with_cli_instruction(self):
        """Should disable profiling when CLI instruction provided."""
        config = Mock(spec=Config)
        config.provider = "glm"
        config.identity = "code"

        with (
            patch("cc.agent._create_llm"),
            patch("cogency.tools") as mock_tools,
            patch("cc.agent.Agent") as mock_agent_class,
        ):
            mock_tools.category.return_value = []
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            create_agent(config, cli_instruction="fix this bug")

            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["profile"] is False
            assert "fix this bug" in call_kwargs["instructions"]

    def test_create_agent_invalid_provider(self):
        """Should raise ValueError for unknown provider."""
        config = Mock(spec=Config)
        config.provider = "invalid"
        config.get_api_key.return_value = "test-key"

        with pytest.raises(ValueError, match="Unknown provider: invalid"):
            create_agent(config)


class TestLLMCreation:
    """LLM factory boundary and validation tests."""

    def test_create_openai_with_custom_model(self):
        """Should create OpenAI with custom model."""
        config = Mock(spec=Config)
        config.model = None  # No custom model
        config.get_api_key.return_value = "openai-key"

        with patch("cc.agent.OpenAI") as mock_openai:
            _create_llm("openai", config)
            mock_openai.assert_called_once_with(api_key="openai-key")

    def test_create_glm_default(self):
        """Should create GLM with default config."""
        config = Mock(spec=Config)
        config.get_api_key.return_value = "glm-key"

        with patch("cc.agent.GLM") as mock_glm:
            _create_llm("glm", config)
            mock_glm.assert_called_once_with(api_key="glm-key")

    def test_model_name_resolution(self):
        """Should resolve model names correctly."""
        llm_with_http = Mock()
        llm_with_http.http_model = "claude-3-sonnet"

        llm_without_http = Mock(spec=[])
        del llm_without_http.http_model

        assert _get_model_name(llm_with_http, "anthropic") == "claude-3-sonnet"
        assert _get_model_name(llm_without_http, "glm") == "GLM"

    def test_security_boundary_enforced(self):
        """Should always enforce project-level security."""
        config = Mock(spec=Config)
        config.provider = "openai"
        config.identity = "code"
        config.get_api_key.return_value = "test-key"

        with (
            patch("cogency.tools"),
            patch("cc.agent.load_instructions"),
            patch("cc.agent.get_identity"),
            patch("cc.agent._create_llm"),
            patch("cc.agent.Agent") as mock_agent,
        ):
            create_agent(config)

            # Verify security boundary
            call_args = mock_agent.call_args
            assert call_args[1]["security"].access == "project"
