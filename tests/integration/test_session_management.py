import json

import pytest


@pytest.mark.asyncio
async def test_save_and_list_session(cli_runner, clean_config_file):
    cli_runner(["hello world", "--new", "--gemini"])
    result = cli_runner(["--save", "my_session"])
    assert "Session 'my_session' overwritten." in result.stdout

    # Verify the config file was updated
    with open(clean_config_file) as f:
        config_data = json.load(f)
    assert config_data["provider"] == "gemini"

    result = cli_runner(["--saves"])
    assert "my_session" in result.stdout
    assert "gemini/gemini-2.5-flash" in result.stdout


@pytest.mark.asyncio
async def test_save_overwrite_and_resume(cli_runner, clean_config_file, monkeypatch):
    cli_runner(["first message", "--new", "--gemini"])
    cli_runner(["--save", "overwrite_test"])

    cli_runner(["second message", "--new", "--claude"])
    monkeypatch.setattr("builtins.input", lambda _: "y")
    result = cli_runner(["--save", "overwrite_test"])
    assert "Session 'overwrite_test' overwritten." in result.stdout

    # Verify the config file was updated
    with open(clean_config_file) as f:
        config_data = json.load(f)
    assert config_data["provider"] == "anthropic"

    result = cli_runner(["--resume", "overwrite_test", "--query"])
    assert "Resuming session with tag: overwrite_test" in result.stdout


@pytest.mark.asyncio
async def test_resume_non_existent(cli_runner):
    result = cli_runner(["--resume", "non_existent"], expected_exit_code=1)
    assert "Error: Session with tag 'non_existent' not found." in result.stderr


@pytest.mark.asyncio
async def test_set_model(cli_runner, clean_config_file):
    result = cli_runner(["--set", "model", "codex"])
    assert "Model set to: openai/gpt-5-codex-low" in result.stdout


@pytest.mark.asyncio
async def test_set_invalid_model(cli_runner):
    result = cli_runner(["--set", "model", "invalid"], expected_exit_code=1)
    assert "Error: Unknown model alias 'invalid'." in result.stderr
