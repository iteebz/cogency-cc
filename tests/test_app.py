"""Tests for the main CogencyCode TUI application."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cogency_code.app import CogencyCode


def test_app_initialization():
    """Test app initialization with default parameters."""
    # Mock environment to avoid API calls during testing
    with patch.dict(os.environ, {"GLM_API_KEY": "test-key"}):
        with patch("cogency_code.app.create_agent"):
            # Mock Config to start with fresh defaults
            with patch("cogency_code.app.Config") as mock_config:
                mock_config.return_value.provider = "glm"
                mock_config.return_value.mode = "auto"
                mock_config.return_value.get_api_key.return_value = "test-key"

                app = CogencyCode()

                assert app.llm_provider == "glm"
                assert isinstance(app.conversation_id, str)
                assert app.user_id == "cogency"
                assert app.mode == "auto"
                assert hasattr(app, "agent")


def test_app_initialization_custom_params():
    """Test app initialization with custom parameters."""
    with patch.dict(os.environ, {"GLM_API_KEY": "test-key"}):
        with patch("cogency_code.app.create_agent"):
            with patch("cogency_code.app.Config") as mock_config:
                mock_config.return_value.provider = "glm"
                mock_config.return_value.mode = "auto"
                mock_config.return_value.get_api_key.return_value = "test-key"

                app = CogencyCode(
                    llm_provider="glm",
                    mode="resume",
                )

                assert app.llm_provider == "glm"
                assert isinstance(app.conversation_id, str)
                assert app.user_id == "custom_user"
                assert app.mode == "resume"


@pytest.mark.asyncio
async def test_app_compose():
    """Test app widget composition."""
    with patch("cogency_code.app.create_agent"):
        with patch("cogency_code.app.Config") as mock_config:
            mock_config.return_value.provider = "glm"
            mock_config.return_value.get_api_key.return_value = "test-key"

            app = CogencyCode()
            async with app.run_test():
                widgets = list(app.compose())

                widget_types = [type(widget).__name__ for widget in widgets]
                assert "Header" in widget_types
                assert "StreamView" in widget_types
                assert "Footer" in widget_types


def test_action_clear():
    """Test clear action."""
    with patch("cogency_code.app.create_agent"):
        with patch("cogency_code.app.Config") as mock_config:
            mock_config.return_value.provider = "glm"
            mock_config.return_value.get_api_key.return_value = "test-key"

            app = CogencyCode()
            app.stream_view = MagicMock()

            app.action_clear()
            app.stream_view.clear.assert_called_once()


def test_action_toggle_config():
    """Test config toggle action."""
    with patch("cogency_code.app.create_agent"):
        with patch("cogency_code.app.Config") as mock_config:
            mock_config.return_value.provider = "glm"
            mock_config.return_value.get_api_key.return_value = "test-key"

            app = CogencyCode()
            app.push_screen = MagicMock()

            app.action_toggle_config()
            app.push_screen.assert_called_once()
            args, kwargs = app.push_screen.call_args
            assert len(args) == 2  # screen and callback


@pytest.mark.asyncio
async def test_on_footer_config_requested():
    """Test handling config request from footer."""
    with patch("cogency_code.app.create_agent"):
        with patch("cogency_code.app.Config") as mock_config:
            mock_config.return_value.provider = "glm"
            mock_config.return_value.get_api_key.return_value = "test-key"

            app = CogencyCode()
            app.push_screen = AsyncMock()
            mock_event = MagicMock()
            app.header = MagicMock()  # Mock app.header

            await app._config_updated(mock_event)
            app.push_screen.assert_called_once()
