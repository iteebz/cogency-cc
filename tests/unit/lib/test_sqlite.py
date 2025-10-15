import os
import tempfile
from pathlib import Path

import pytest
from cogency.lib.sqlite import DB, SQLite


@pytest.mark.asyncio
async def test_relative_path_from_readonly_dir():
    """Regression: SQLite with relative path fails when cwd is readonly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        readonly_dir = f"{tmpdir}/readonly"
        Path(readonly_dir).mkdir()
        os.chmod(readonly_dir, 0o555)

        orig_cwd = os.getcwd()
        try:
            os.chdir(readonly_dir)
            storage = SQLite()

            with pytest.raises(Exception) as exc_info:
                await storage.load_profile("test")

            err_str = str(exc_info.value).lower()
            assert "permission denied" in err_str or "unable to open" in err_str
        finally:
            os.chdir(orig_cwd)
            os.chmod(readonly_dir, 0o755)


def test_connect_creates_db_in_nonexistent_dir():
    """Regression: DB.connect must work when parent dir and file don't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/nonexistent/.cogency/store.db"
        assert not Path(db_path).exists()

        conn = DB.connect(db_path)
        conn.close()

        assert Path(db_path).exists()
        assert Path(db_path).parent.exists()


def test_connect_initializes_schema():
    """DB.connect must create tables on first connection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/store.db"

        conn = DB.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "messages" in tables
        assert "events" in tables
        assert "profiles" in tables


def test_connect_idempotent():
    """Multiple connects to same path should work."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/store.db"

        conn1 = DB.connect(db_path)
        conn1.close()

        conn2 = DB.connect(db_path)
        conn2.close()
