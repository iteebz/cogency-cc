import pytest

from cc.storage.summaries import Summaries


@pytest.fixture
def summaries_storage(tmp_path):
    """Fixture to create a Summaries instance with a temporary database."""
    db_path = tmp_path / "test_summaries.db"
    return Summaries(str(db_path))


@pytest.mark.asyncio
async def test_summaries_storage_initialization(summaries_storage):
    # The initialization check is implicitly done by the fixture setup.
    # We can add a more explicit check if needed, but for now, if the fixture
    # doesn't fail, the schema is created.
    pass


@pytest.mark.asyncio
async def test_save_and_load_summary(summaries_storage):
    conversation_id = "conv1"
    user_id = "user1"
    summary_text = "This is a test summary."
    message_count = 10
    start_ts = 1678886400.0
    end_ts = 1678887000.0

    summary_id = await summaries_storage.save_summary(
        conversation_id, user_id, summary_text, message_count, start_ts, end_ts
    )
    assert summary_id is not None

    summaries = await summaries_storage.load_summaries(conversation_id)
    assert len(summaries) == 1
    saved_summary = summaries[0]
    assert saved_summary["summary"] == summary_text
    assert saved_summary["count"] == message_count


@pytest.mark.asyncio
async def test_load_nonexistent_conversation(summaries_storage):
    summaries = await summaries_storage.load_summaries("nonexistent-conv")
    assert len(summaries) == 0
