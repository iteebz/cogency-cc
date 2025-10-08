"""Test storage layer operations and database handling."""

import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cc.storage import SummaryStorage


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = Path.cwd()
        os.chdir(temp_dir)
        try:
            db_path = Path(temp_dir) / "test.db"
            storage = SummaryStorage(db_path=str(db_path))
            yield storage
        finally:
            os.chdir(original_cwd)


@pytest.mark.asyncio
async def test_storage_initialization(temp_storage):
    """Test storage creates database and tables correctly."""
    with sqlite3.connect(temp_storage.db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ["summaries"]
        for table in expected_tables:
            assert table in tables


@pytest.mark.asyncio
async def test_save_and_load_summary(temp_storage):
    """Test saving and loading conversation summaries."""
    summary_id = await temp_storage.save_summary(
        "conv-1", "user-1", "Conversation summary", 5, 1640995200.0, 1640995300.0
    )
    assert summary_id is not None
    assert len(summary_id) > 0
    summaries = await temp_storage.load_summaries("conv-1")
    assert len(summaries) == 1
    assert summaries[0]["summary"] == "Conversation summary"
    assert summaries[0]["count"] == 5


@pytest.mark.asyncio
async def test_load_nonexistent_conversation(temp_storage):
    """Test loading summaries from non-existent conversation."""
    summaries = await temp_storage.load_summaries("nonexistent")
    assert summaries == []


@pytest.mark.asyncio
async def test_cull_messages(temp_storage):
    """Test message culling functionality."""
    with sqlite3.connect(temp_storage.db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            INSERT INTO messages VALUES
                ('msg-1', 'conv-1', 'user-1', 'system', 'System msg', 1640995000.0),
                ('msg-2', 'conv-1', 'user-1', 'user', 'User msg 1', 1640995100.0),
                ('msg-3', 'conv-1', 'user-1', 'assistant', 'Assistant msg 1', 1640995200.0),
                ('msg-4', 'conv-1', 'user-1', 'user', 'User msg 2', 1640995300.0);
        """)
    culled = await temp_storage.cull_messages("conv-1", 1640995250.0, keep_system=True)
    assert culled == 2
    cursor = sqlite3.connect(temp_storage.db_path).execute(
        "SELECT type FROM messages WHERE conversation_id = 'conv-1' ORDER BY timestamp"
    )
    remaining = [row[0] for row in cursor.fetchall()]
    assert remaining == ["system", "user"]


@pytest.mark.asyncio
async def test_cull_messages_without_keeping_system(temp_storage):
    """Test message culling without keeping system messages."""
    with sqlite3.connect(temp_storage.db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            INSERT INTO messages VALUES
                ('msg-1', 'conv-1', 'user-1', 'system', 'System msg', 1640995000.0),
                ('msg-2', 'conv-1', 'user-1', 'user', 'User msg 1', 1640995100.0);
        """)
    culled = await temp_storage.cull_messages("conv-1", 1640995250.0, keep_system=False)
    assert culled == 2


@pytest.mark.asyncio
async def test_secure_path_resolution_default(tmp_path):
    """Test secure path resolution with default path."""
    with patch("pathlib.Path.cwd", return_value=tmp_path):
        storage = SummaryStorage()  # No db_path provided
        expected_path = tmp_path / ".cogency" / "store.db"
        assert storage.db_path == str(expected_path)


def test_secure_path_resolution_custom():
    """Test secure path resolution with custom path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = Path.cwd()
        os.chdir(temp_dir)
        try:
            custom_path = Path(temp_dir) / "custom.db"
            storage = SummaryStorage(db_path=str(custom_path))
            assert storage.db_path == str(custom_path.resolve())
        finally:
            os.chdir(original_cwd)


def test_path_traversal_protection():
    """Test protection against path traversal attacks."""
    malicious_path = "../../../etc/passwd"
    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = Path("/safe/dir")
        with pytest.raises(ValueError, match="Database path must be within current directory"):
            SummaryStorage(db_path=malicious_path)


@pytest.mark.asyncio
async def test_concurrent_summary_operations(temp_storage):
    """Test concurrent summary operations don't cause corruption."""
    conv_ids = ["conv-1", "conv-2", "conv-3"]

    async def save_summary(conv_id: str):
        return await temp_storage.save_summary(
            conv_id, "user-1", f"Summary for {conv_id}", 3, 1640995200.0, 1640995300.0
        )

    tasks = [save_summary(conv_id) for conv_id in conv_ids]
    summary_ids = await asyncio.gather(*tasks)
    assert len(summary_ids) == len(set(summary_ids))
    for conv_id in conv_ids:
        summaries = await temp_storage.load_summaries(conv_id)
        assert len(summaries) == 1
        assert summaries[0]["summary"] == f"Summary for {conv_id}"


@pytest.mark.asyncio
async def test_summary_ordering(temp_storage):
    """Test that summaries are loaded in correct chronological order."""
    conv_id = "conv-1"
    summaries_data = [
        ("Third summary", 3, 1640995400.0, 1640995500.0),
        ("Second summary", 2, 1640995200.0, 1640995300.0),
        ("First summary", 1, 1640995000.0, 1640995100.0),
    ]
    for summary_text, count, start_ts, end_ts in reversed(summaries_data):
        await temp_storage.save_summary(conv_id, "user-1", summary_text, count, start_ts, end_ts)
    loaded = await temp_storage.load_summaries(conv_id)
    assert len(loaded) == 3
    assert loaded[0]["summary"] == "First summary"
    assert loaded[1]["summary"] == "Second summary"
    assert loaded[2]["summary"] == "Third summary"


@pytest.mark.asyncio
async def test_multiple_summaries_per_conversation(temp_storage):
    """Test multiple summaries for same conversation."""
    conv_id = "conv-1"
    for i in range(3):
        await temp_storage.save_summary(
            conv_id,
            "user-1",
            f"Summary {i + 1}",
            i + 1,
            1640995200.0 + i * 100,
            1640995300.0 + i * 100,
        )
    summaries = await temp_storage.load_summaries(conv_id)
    assert len(summaries) == 3
    for i, summary in enumerate(summaries):
        assert summary["summary"] == f"Summary {i + 1}"
        assert summary["count"] == i + 1


def test_database_schema_initialization(temp_storage):
    """Test that database schema is properly initialized."""
    with sqlite3.connect(temp_storage.db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(summaries)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = [
            "summary_id",
            "conversation_id",
            "user_id",
            "summary",
            "message_count",
            "start_timestamp",
            "end_timestamp",
            "created_at",
        ]
        for col in expected_columns:
            assert col in columns
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_summaries_conversation'"
        )
        index_exists = cursor.fetchone() is not None
        assert index_exists
