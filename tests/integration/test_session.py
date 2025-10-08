import uuid

from typer.testing import CliRunner

from cc.cli import app as cli


def test_save_and_list_session(config, snapshots, capsys):
    config.conversation_id = "test_conv_1"
    config.provider = "gemini"
    config.model = "gemini-2.5-flash"
    config.save()

    runner = CliRunner()
    unique_tag = str(uuid.uuid4())
    result = runner.invoke(cli, ["session", "save", unique_tag])
    assert result.exit_code == 0
    assert f"Session saved with tag: {unique_tag}" in result.output

    result = runner.invoke(cli, ["session", "list"])
    assert result.exit_code == 0
    assert unique_tag in result.output


def test_save_overwrite_and_resume(config, snapshots, capsys):
    config.conversation_id = "conv_old"
    config.provider = "gemini"
    config.save()

    runner = CliRunner()
    runner.invoke(cli, ["session", "save", "overwrite_test"])
    config.conversation_id = "conv_new"
    config.provider = "anthropic"
    config.save()

    result = runner.invoke(cli, ["session", "save", "overwrite_test"], input="y\n")
    assert result.exit_code == 0
    assert "Session 'overwrite_test' overwritten." in result.output

    result = runner.invoke(cli, ["session", "resume", "overwrite_test"])
    assert result.exit_code == 0
    assert "Resumed session 'overwrite_test'." in result.output


def test_resume_non_existent(capsys):
    runner = CliRunner()
    result = runner.invoke(cli, ["session", "resume", "non_existent"])
    assert result.exit_code != 0
    assert "Invalid value: Session with tag 'non_existent' not found." in result.output
