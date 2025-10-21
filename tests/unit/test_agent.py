"""Core agent behavior and contract tests."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cc.agent import _create_llm, create_agent
from cc.cc_md import CC_IDENTITY
from cc.config import Config


def test_create_agent_with_default_config():
    config = Mock(spec=Config)
    config.provider = "openai"
    config.model = "gpt-4"
    config.identity = "code"
    config.get_api_key.return_value = "test-key"
    config.config_dir = Path("/tmp/.cogency")

    with (
        patch("cogency.tools") as mock_tools,
        patch("cc.cc_md.load") as mock_cc_md_load,
    ):
        mock_tools.category.return_value = ["file_tool", "system_tool"]
        mock_cc_md_load.return_value = (
            "--- User .cogency/cc.md ---\nHelp with coding\n--- End .cogency/cc.md ---"
        )

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
            assert call_kwargs["mode"] == "replay"
            assert "Help with coding" in call_kwargs["instructions"]
            assert "--- User .cogency/cc.md ---" in call_kwargs["instructions"]


def test_create_agent_with_cli_instruction():
    config = Mock(spec=Config)
    config.get_api_key.return_value = "test-key"
    config.model = "some-model"
    config.config_dir = Path("/tmp/.cogency")

    with (
        patch("cc.agent._create_llm"),
        patch("cogency.tools") as mock_tools,
        patch("cc.agent.Agent") as mock_agent_class,
        patch("cc.cc_md.load") as mock_cc_md_load,
    ):
        mock_tools.category.return_value = []
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        mock_cc_md_load.return_value = (
            "--- User .cogency/cc.md ---\nProject instructions\n--- End .cogency/cc.md ---"
        )

        create_agent(config, cli_instruction="fix this bug")

        call_kwargs = mock_agent_class.call_args[1]
        assert call_kwargs["profile"] is False
        assert "fix this bug" in call_kwargs["instructions"]
        assert "Project instructions" in call_kwargs["instructions"]
        assert "--- User .cogency/cc.md ---" in call_kwargs["instructions"]


def test_create_agent_invalid_provider():
    config = Mock(spec=Config)
    config.provider = "invalid"
    config.model = ""
    config.get_api_key.return_value = "test-key"

    with pytest.raises(ValueError, match="Unknown provider: invalid"):
        create_agent(config)


def test_create_openai_with_custom_model():
    config = Mock(spec=Config)
    config.model = "some-model"
    config.get_api_key.return_value = "openai-key"

    with patch("cc.agent.OpenAI") as mock_openai:
        _create_llm("openai", config)
        mock_openai.assert_called_once_with(api_key="openai-key", http_model="some-model")


def test_create_glm_default():
    config = Mock(spec=Config)
    config.model = "some-model"
    config.get_api_key.return_value = "glm-key"

    with patch("cc.agent.GLM") as mock_glm:
        _create_llm("glm", config)
        mock_glm.assert_called_once_with(api_key="glm-key", http_model="some-model")


def test_security_boundary_enforced():
    config = Mock(spec=Config)
    config.provider = "openai"
    config.identity = "code"
    config.get_api_key.return_value = "test-key"
    config.model = "some-model"
    config.config_dir = Path("/tmp/.cogency")

    with (
        patch("cogency.tools"),
        patch("cc.cc_md.load") as mock_cc_md_load,
        patch("cc.agent._create_llm"),
        patch("cc.agent.Agent") as mock_agent,
    ):
        mock_cc_md_load.return_value = None
        create_agent(config)

        call_args = mock_agent.call_args
        assert call_args[1]["security"].access == "project"
        assert "Working directory:" in call_args[1]["instructions"]


def test_coding_structure():
    coding_identity = CC_IDENTITY
    assert "Surgical coding cli agent" in coding_identity
    assert "MANDATE" not in coding_identity
    assert "PRINCIPLES" in coding_identity
    assert "EXECUTION" in coding_identity
    assert "RUNTIME" not in coding_identity
    assert "SECURITY" not in coding_identity

    assert "- Explore before acting" in coding_identity
    assert "- Ground claims in tool output" in coding_identity
    assert "- Minimal edits over rewrites" in coding_identity
