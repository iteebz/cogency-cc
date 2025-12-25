from pathlib import Path

import pytest

from cc.config import Config
from cc.storage import Snapshots


@pytest.fixture
def project_root(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("project")
    (path / ".cogency").mkdir()
    return path


@pytest.fixture
def snapshots(project_root: Path) -> Snapshots:
    db_path = project_root / ".cogency" / "snapshots.db"
    return Snapshots(db_path=str(db_path))


@pytest.fixture
def config(project_root: Path) -> Config:
    config_dir = project_root / ".cogency"
    return Config(config_dir=config_dir, user_id="test_user")
