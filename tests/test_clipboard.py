"""Test clipboard functionality in StreamView widget."""

from unittest.mock import Mock, PropertyMock, patch

import pytest
from textual.widgets import Static

from cogency_code.widgets.stream import StreamView


class TestStreamViewClipboard:
    """Test clipboard operations in StreamView."""

    @pytest.fixture
    def stream_view(self):
        """Create a StreamView instance for testing."""
        view = StreamView()
        # Mock the app property to avoid needing full Textual setup
        mock_app = Mock()
        mock_app.notify = Mock()
        type(view).app = PropertyMock(return_value=mock_app)
        return view

    def test_copy_last_content_success(self, stream_view):
        """Test successful copy of last content to clipboard."""
        # Manually add a child widget to simulate content
        static_widget = Static("Test response")
        # Mock the children property to return our test widget
        type(stream_view).children = PropertyMock(return_value=[static_widget])

        with patch("pyperclip.copy") as mock_copy:
            stream_view.action_copy_selection()
            mock_copy.assert_called_once_with("Test response")

    def test_copy_empty_content(self, stream_view):
        """Test copy when no content is available."""
        type(stream_view).children = PropertyMock(return_value=[])

        with patch("pyperclip.copy") as mock_copy:
            stream_view.action_copy_selection()
            mock_copy.assert_not_called()

    def test_copy_handles_clipboard_error(self, stream_view):
        """Test graceful handling of clipboard errors."""
        static_widget = Static("Test content")
        type(stream_view).children = PropertyMock(return_value=[static_widget])

        with patch("pyperclip.copy", side_effect=Exception("Clipboard error")):
            with patch.object(stream_view.app, "notify") as mock_notify:
                stream_view.action_copy_selection()
                mock_notify.assert_called_once_with("Failed to copy to clipboard", severity="error")

    def test_copy_user_content(self, stream_view):
        """Test copying user input content."""
        static_widget = Static("User input here")
        type(stream_view).children = PropertyMock(return_value=[static_widget])

        with patch("pyperclip.copy") as mock_copy:
            stream_view.action_copy_selection()
            mock_copy.assert_called_once_with("User input here")

    def test_copy_call_content(self, stream_view):
        """Test copying tool call content."""
        static_widget = Static("Tool called with args")
        type(stream_view).children = PropertyMock(return_value=[static_widget])

        with patch("pyperclip.copy") as mock_copy:
            stream_view.action_copy_selection()
            mock_copy.assert_called_once_with("Tool called with args")

    def test_get_last_content_empty(self, stream_view):
        """Test getting content from empty view."""
        type(stream_view).children = PropertyMock(return_value=[])
        content = stream_view._get_last_content()
        assert content == ""

    def test_get_last_content_with_children(self, stream_view):
        """Test extracting content from child widgets."""
        static_widget = Static("Last message")
        type(stream_view).children = PropertyMock(return_value=[static_widget])

        content = stream_view._get_last_content()
        assert content == "Last message"

    def test_copy_binding_exists(self, stream_view):
        """Test that copy binding is properly configured."""
        bindings = [binding for binding in stream_view.BINDINGS if binding.key == "ctrl+c"]
        assert len(bindings) == 1
        assert bindings[0].action == "copy_selection"
