from cc.config import Config


def test_default_user_id_is_cc_user():
    config = Config()
    assert config.user_id == "cc_user"


def test_custom_user_id_persists():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".cogency"
        config_dir.mkdir()

        config = Config(user_id="custom_user")
        config.config_dir = config_dir
        config.config_file = config_dir / "cc.json"
        config.save()

        config2 = Config()
        config2.config_dir = config_dir
        config2.config_file = config_dir / "cc.json"
        config2.load()

        assert config2.user_id == "custom_user"
