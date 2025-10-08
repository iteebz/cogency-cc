"""Core conversation behavior and contract tests."""

from unittest.mock import MagicMock, patch

from cc.conversations import _format_time_ago, get_last_conversation, list_conversations


def test_format_time_ago():
    """Should format time correctly at key boundaries."""
    import time

    now = time.time()

    # Edge cases
    assert _format_time_ago(now) == "Just now"
    assert _format_time_ago(now - 30) == "Just now"
    assert _format_time_ago(now - 60) == "1m ago"
    assert _format_time_ago(now - 3600) == "1h ago"
    assert _format_time_ago(now - 86400) == "1d ago"
    assert _format_time_ago(now - 604800) == "1w ago"


def test_list_convs_no_db():
    """Should return empty list when database doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = list_conversations()
        import asyncio

        conversations = asyncio.run(result)

        assert conversations == []


def test_get_last_conv_no_db():
    """Should return None when database doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        conv_id = get_last_conversation()
        assert conv_id is None


def test_list_convs_query_structure():
    """Should query database with expected SQL structure."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.__truediv__"),
    ):
        # Mock database connection
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_db.__enter__.return_value = mock_db
        mock_db.execute.return_value = mock_cursor

        with patch("sqlite3.connect", return_value=mock_db):
            result = list_conversations(limit=5)
            import asyncio

            asyncio.run(result)

            # Verify SQL query structure
            call_args = mock_db.execute.call_args[0]
            query = call_args[0]
            assert "SELECT" in query
            assert "conversation_id" in query
            assert "ORDER BY" in query
            assert "LIMIT ?" in query

            # Verify limit parameter
            assert call_args[1] == (5,)


def test_get_last_conv_by_timestamp():
    """Should query for most recent conversation by timestamp."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.__truediv__"),
    ):
        # Mock database returning no results
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.__enter__.return_value = mock_db
        mock_db.execute.return_value = mock_cursor

        with patch("sqlite3.connect", return_value=mock_db):
            get_last_conversation()

            # Verify SQL structure
            call_args = mock_db.execute.call_args[0]
            query = call_args[0]
            assert "ORDER BY timestamp DESC" in query
            assert "LIMIT 1" in query


def test_conv_result_contract():
    """Should return conversations with required contract fields."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.__truediv__"),
    ):
        # Mock database with test data
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("conv1", "user1", "Test message content", 1234567890, 3)
        ]
        mock_db.__enter__.return_value = mock_db
        mock_db.execute.return_value = mock_cursor

        with (
            patch("sqlite3.connect", return_value=mock_db),
            patch("time.time", return_value=1234568000),
        ):
            result = list_conversations(limit=10)
            import asyncio

            conversations = asyncio.run(result)

            # Verify contract structure
            assert len(conversations) == 1
            conv = conversations[0]

            required_fields = [
                "conversation_id",
                "user_id",
                "preview",
                "timestamp",
                "message_count",
                "time_ago",
            ]
            for field in required_fields:
                assert field in conv, f"Missing field: {field}"

            # Verify field types
            assert isinstance(conv["conversation_id"], str)
            assert isinstance(conv["user_id"], str)
            assert isinstance(conv["preview"], str)
            assert isinstance(conv["timestamp"], (int, float))
            assert isinstance(conv["message_count"], int)
            assert isinstance(conv["time_ago"], str)


def test_preview_truncation():
    """Should truncate long message previews correctly."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.__truediv__"),
    ):
        # Mock database with long message
        long_message = "This is a very long message that should be truncated"
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("conv1", "user1", long_message, 1234567890, 1)]
        mock_db.__enter__.return_value = mock_db
        mock_db.execute.return_value = mock_cursor

        with (
            patch("sqlite3.connect", return_value=mock_db),
            patch("time.time", return_value=1234568000),
        ):
            result = list_conversations(limit=10)
            import asyncio

            conversations = asyncio.run(result)

            conv = conversations[0]
            # Should truncate long messages
            assert len(conv["preview"]) <= 53  # 50 + "..."
            if len(long_message) > 50:
                assert conv["preview"].endswith("...")


def test_conv_ordering():
    """Should return conversations ordered by most recent first."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.__truediv__"),
    ):
        # Mock database with conversations in reverse chronological order
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("conv2", "user1", "New message", 1234567990, 1),  # Newer
            ("conv1", "user1", "Old message", 1234567890, 2),  # Older
        ]
        mock_db.__enter__.return_value = mock_db
        mock_db.execute.return_value = mock_cursor

        with (
            patch("sqlite3.connect", return_value=mock_db),
            patch("time.time", return_value=1234568000),
        ):
            result = list_conversations(limit=10)
            import asyncio

            conversations = asyncio.run(result)

            # Should be ordered by timestamp descending
            timestamps = [c["timestamp"] for c in conversations]
            assert timestamps == sorted(timestamps, reverse=True)
            assert conversations[0]["conversation_id"] == "conv2"  # Newer first
