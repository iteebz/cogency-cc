import asyncio
import uuid
from unittest.mock import patch

import pytest

from cc.cli import app as cli


@pytest.mark.asyncio
@patch("cc.cli.run_agent")
async def test_save_and_list_session(mock_run_agent, config, snapshots, cli_runner):
    config.conversation_id = "test_conv_1"
    config.provider = "gemini"
    config.model = "gemini-2.5-flash"
    config.save()

    unique_tag = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, cli_runner.invoke, cli, ["session", "save", unique_tag]
    )
    assert result.exit_code == 0
    assert f"Session saved with tag: {unique_tag}" in result.output

    result = await loop.run_in_executor(None, cli_runner.invoke, cli, ["session", "list"])
    assert result.exit_code == 0
    assert unique_tag in result.output


@pytest.mark.asyncio
@patch("cc.cli.run_agent")
async def test_save_overwrite_and_resume(mock_run_agent, config, snapshots, cli_runner):
    config.conversation_id = "conv_old"
    config.provider = "gemini"
    config.save()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, cli_runner.invoke, cli, ["session", "save", "overwrite_test"])
    config.conversation_id = "conv_new"
    config.provider = "anthropic"
    config.save()

    result = await loop.run_in_executor(
        None, cli_runner.invoke, cli, ["session", "save", "overwrite_test"]
    )
    assert result.exit_code == 0
    assert "Session saved with tag: overwrite_test" in result.output

    result = await loop.run_in_executor(
        None, cli_runner.invoke, cli, ["session", "resume", "overwrite_test"]
    )
    assert result.exit_code == 0
    assert "Resumed session 'overwrite_test'." in result.output


@pytest.mark.asyncio
@patch("cc.cli.run_agent")
async def test_resume_non_existent(mock_run_agent, cli_runner):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, cli_runner.invoke, cli, ["session", "resume", "non_existent"]
    )
    assert result.exit_code != 0
    assert "Invalid value: Session with tag 'non_existent' not found." in result.output
