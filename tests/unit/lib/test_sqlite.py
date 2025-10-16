import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from cogency.lib.sqlite import SQLite

from cc.lib.sqlite import DB, Snapshots
from src.cc.config import Config


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


def test_connect_creates_empty_db():
    """DB.connect creates an empty database (schema initialized by callers)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/store.db"

        conn = DB.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert len(tables) == 0


def test_connect_idempotent():
    """Multiple connects to same path should work."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/store.db"

        conn1 = DB.connect(db_path)
        conn1.close()

        conn2 = DB.connect(db_path)
        conn2.close()


@pytest.fixture
def snapshots_storage(tmp_path):
    """Fixture to create a Snapshots instance with a temporary database."""
    db_path = tmp_path / ".cogency" / "test_store.db"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    yield Snapshots(db_path=str(db_path))
    if Path(db_path).exists():
        os.remove(db_path)


@pytest.mark.asyncio
async def test_save_and_load_session(snapshots_storage):
    tag = "test_tag"
    conv_id = "test_conv_id"
    user_id = "test_user"
    config = Config(provider="test_provider", model="test_model", user_id=user_id)

    await snapshots_storage.save_session(tag, conv_id, user_id, config.to_dict())

    loaded_data = await snapshots_storage.load_session(tag, user_id)
    assert loaded_data is not None
    assert loaded_data["conversation_id"] == conv_id
    assert loaded_data["model_config"]["provider"] == "test_provider"
    assert loaded_data["model_config"]["model"] == "test_model"


@pytest.mark.asyncio
async def test_overwrite_session(snapshots_storage):
    tag = "overwrite_tag"
    conv_id_old = "conv_old"
    conv_id_new = "conv_new"
    user_id = "user_overwrite"
    config_old = Config(provider="old_provider", model="old_model", user_id=user_id)
    config_new = Config(provider="new_provider", model="new_model", user_id=user_id)

    await snapshots_storage.save_session(tag, conv_id_old, user_id, config_old.to_dict())
    await snapshots_storage.overwrite_session(tag, conv_id_new, user_id, config_new.to_dict())

    loaded_data = await snapshots_storage.load_session(tag, user_id)
    assert loaded_data is not None
    assert loaded_data["conversation_id"] == conv_id_new
    assert loaded_data["model_config"]["provider"] == "new_provider"
    assert loaded_data["model_config"]["model"] == "new_model"


@pytest.mark.asyncio
async def test_list_sessions(snapshots_storage):
    user_id = "list_user"
    config = Config(user_id=user_id)

    await snapshots_storage.save_session("tag1", "conv1", user_id, config.to_dict())
    await asyncio.sleep(0.01)
    await snapshots_storage.save_session("tag2", "conv2", user_id, config.to_dict())

    sessions = await snapshots_storage.list_sessions(user_id)
    assert len(sessions) == 2
    assert sessions[0]["tag"] == "tag2"
    assert sessions[1]["tag"] == "tag1"


@pytest.mark.asyncio
async def test_load_non_existent_session(snapshots_storage):
    user_id = "non_existent_user"
    loaded_data = await snapshots_storage.load_session("non_existent_tag", user_id)
    assert loaded_data is None


@pytest.mark.asyncio
async def test_save_session_different_users(snapshots_storage):
    tag = "shared_tag"
    conv_id = "conv_shared"
    user_id1 = "user_a"
    user_id2 = "user_b"
    config = Config(user_id=user_id1)

    await snapshots_storage.save_session(tag, conv_id, user_id1, config.to_dict())

    config2 = Config(user_id=user_id2)
    await snapshots_storage.save_session(tag, conv_id, user_id2, config2.to_dict())

    sessions_user1 = await snapshots_storage.list_sessions(user_id1)
    sessions_user2 = await snapshots_storage.list_sessions(user_id2)

    assert len(sessions_user1) == 1
    assert sessions_user1[0]["tag"] == tag
    assert len(sessions_user2) == 1
    assert sessions_user2[0]["tag"] == tag

    loaded_data1 = await snapshots_storage.load_session(tag, user_id1)
    loaded_data2 = await snapshots_storage.load_session(tag, user_id2)

    assert loaded_data1["model_config"]["user_id"] == user_id1
    assert loaded_data2["model_config"]["user_id"] == user_id2
