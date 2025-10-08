import sqlite3
from pathlib import Path


class DB:
    _initialized_paths = set()

    @classmethod
    def connect(cls, db_path: str):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Schema initialization is now handled by the specific storage classes
        # to allow for different table structures in the same DB file.
        # We only ensure the directory exists here.

        return sqlite3.connect(path)
