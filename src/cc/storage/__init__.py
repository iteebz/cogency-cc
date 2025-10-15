from cogency.lib.sqlite import SQLite

from ..state import Config
from .db import DB as DB
from .snapshots import Snapshots as Snapshots


def storage(config: Config) -> SQLite:
    return SQLite(str(config.config_dir / "store.db"))
