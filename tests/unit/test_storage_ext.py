import asyncio
import os
from pathlib import Path

import pytest

from src.cc.state import Config
from src.cc.storage_ext import StorageExt


@pytest.fixture
def session_storage_path(tmp_path):
    db_path = tmp_path / ".cogency" / "test_store.db"
    return str(db_path)


@pytest.fixture
def session_storage(session_storage_path):
    # Ensure the directory exists for the DB
    Path(session_storage_path).parent.mkdir(parents=True, exist_ok=True)
    yield StorageExt(db_path=session_storage_path)
    # Clean up the database file after tests
    if Path(session_storage_path).exists():
        os.remove(session_storage_path)


@pytest.mark.asyncio
async def test_save_and_load_session(session_storage):
    tag = "test_tag"
    conv_id = "test_conv_id"
    user_id = "test_user"
    config = Config(provider="test_provider", model="test_model", user_id=user_id)

    await session_storage.save_session(tag, conv_id, user_id, config.to_dict())

    loaded_data = await session_storage.load_session(tag, user_id)
    assert loaded_data is not None
    assert loaded_data["conversation_id"] == conv_id
    assert loaded_data["model_config"]["provider"] == "test_provider"
    assert loaded_data["model_config"]["model"] == "test_model"


@pytest.mark.asyncio
async def test_overwrite_session(session_storage):
    tag = "overwrite_tag"
    conv_id_old = "conv_old"
    conv_id_new = "conv_new"
    user_id = "user_overwrite"
    config_old = Config(provider="old_provider", model="old_model", user_id=user_id)
    config_new = Config(provider="new_provider", model="new_model", user_id=user_id)

    await session_storage.save_session(tag, conv_id_old, user_id, config_old.to_dict())
    await session_storage.overwrite_session(tag, conv_id_new, user_id, config_new.to_dict())

    loaded_data = await session_storage.load_session(tag, user_id)
    assert loaded_data is not None
    assert loaded_data["conversation_id"] == conv_id_new
    assert loaded_data["model_config"]["provider"] == "new_provider"
    assert loaded_data["model_config"]["model"] == "new_model"


@pytest.mark.asyncio
async def test_list_sessions(session_storage):
    user_id = "list_user"
    config = Config(user_id=user_id)

    await session_storage.save_session("tag1", "conv1", user_id, config.to_dict())
    await asyncio.sleep(0.01)  # Ensure different timestamps
    await session_storage.save_session("tag2", "conv2", user_id, config.to_dict())

    sessions = await session_storage.list_sessions(user_id)
    assert len(sessions) == 2
    assert sessions[0]["tag"] == "tag2"  # Ordered by created_at DESC
    assert sessions[1]["tag"] == "tag1"


@pytest.mark.asyncio
async def test_load_non_existent_session(session_storage):
    user_id = "non_existent_user"
    loaded_data = await session_storage.load_session("non_existent_tag", user_id)
    assert loaded_data is None


@pytest.mark.asyncio
async def test_save_session_different_users(session_storage):
    tag = "shared_tag"
    conv_id = "conv_shared"
    user_id1 = "user_a"
    user_id2 = "user_b"
    config = Config(user_id=user_id1)

    await session_storage.save_session(tag, conv_id, user_id1, config.to_dict())

    # User 2 should be able to save with the same tag
    config2 = Config(user_id=user_id2)
    await session_storage.save_session(tag, conv_id, user_id2, config2.to_dict())

    sessions_user1 = await session_storage.list_sessions(user_id1)
    sessions_user2 = await session_storage.list_sessions(user_id2)

    assert len(sessions_user1) == 1
    assert sessions_user1[0]["tag"] == tag
    assert len(sessions_user2) == 1
    assert sessions_user2[0]["tag"] == tag

    loaded_data1 = await session_storage.load_session(tag, user_id1)
    loaded_data2 = await session_storage.load_session(tag, user_id2)

    assert loaded_data1["model_config"]["user_id"] == user_id1
    assert loaded_data2["model_config"]["user_id"] == user_id2
