"""Tests for agent creation helpers."""

from unittest.mock import MagicMock, patch

import pytest

from cc.agent import _create_llm


@patch("cc.agent.Config")
def test_llm_providers(mock_config_class):
    """Test LLM provider creation for different providers."""
    from cogency.lib.llms.anthropic import Anthropic
    from cogency.lib.llms.gemini import Gemini
    from cogency.lib.llms.openai import OpenAI

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


def test_llm_unknown_provider():
    """Test error handling for unknown LLM providers."""
    mock_config = MagicMock()

    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        _create_llm("unknown", mock_config)
