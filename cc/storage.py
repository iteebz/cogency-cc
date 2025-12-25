"""Consolidated storage: sqlite, sessions, conversations."""

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cogency.lib.resilience import retry
from cogency.lib.uuid7 import uuid7

if TYPE_CHECKING:
    from .config import Config

HOME_DIR = Path.home() / ".cogency"


def get_last_conversation() -> str | None:
    db_path = HOME_DIR / "store.db"
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as db:
        cursor = db.execute("SELECT conversation_id FROM messages ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None


class Snapshots:
    def __init__(self, db_path: Path = HOME_DIR / "store.db"):
        self.db_path = db_path
        self._init_schema()

    def _connect(self):
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(path)

    def _init_schema(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    tag TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    model_config TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(tag, user_id)
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_tag ON sessions(tag);
            """)

    async def save_session(
        self, tag: str, conversation_id: str, user_id: str, model_config: dict[str, Any]
    ) -> str:
        session_id = uuid7()
        model_config_json = json.dumps(model_config)

        def _sync():
            with self._connect() as db:
                db.execute(
                    "INSERT INTO sessions (session_id, tag, conversation_id, user_id, model_config, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, tag, conversation_id, user_id, model_config_json, time.time()),
                )
                return session_id

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _sync)
        except sqlite3.IntegrityError:
            return await self.overwrite_session(tag, conversation_id, user_id, model_config)

    @retry(attempts=3, base_delay=0.1)
    async def overwrite_session(
        self, tag: str, conversation_id: str, user_id: str, model_config: dict[str, Any]
    ) -> str:
        model_config_json = json.dumps(model_config)

        def _sync():
            with self._connect() as db:
                db.execute(
                    "UPDATE sessions SET conversation_id = ?, model_config = ?, created_at = ? WHERE tag = ? AND user_id = ?",
                    (conversation_id, model_config_json, time.time(), tag, user_id),
                )
                return tag

        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    @retry(attempts=3, base_delay=0.1)
    async def delete_session(self, tag: str, user_id: str) -> int:
        def _sync():
            with self._connect() as db:
                cursor = db.execute(
                    "DELETE FROM sessions WHERE tag = ? AND user_id = ?", (tag, user_id)
                )
                return cursor.rowcount

        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    @retry(attempts=3, base_delay=0.1)
    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        def _sync():
            with self._connect() as db:
                db.row_factory = sqlite3.Row
                rows = db.execute(
                    "SELECT tag, conversation_id, created_at, model_config FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
                return [
                    {
                        "tag": row["tag"],
                        "conversation_id": row["conversation_id"],
                        "created_at": row["created_at"],
                        "model_config": json.loads(row["model_config"]),
                    }
                    for row in rows
                ]

        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    @retry(attempts=3, base_delay=0.1)
    async def load_session(self, tag: str, user_id: str) -> dict[str, Any] | None:
        def _sync():
            with self._connect() as db:
                db.row_factory = sqlite3.Row
                row = db.execute(
                    "SELECT tag, conversation_id, created_at, model_config FROM sessions WHERE tag = ? AND user_id = ?",
                    (tag, user_id),
                ).fetchone()
                if row:
                    return {
                        "tag": row["tag"],
                        "conversation_id": row["conversation_id"],
                        "created_at": row["created_at"],
                        "model_config": json.loads(row["model_config"]),
                    }
                return None

        return await asyncio.get_event_loop().run_in_executor(None, _sync)


def storage(config: "Config"):
    from cogency.lib.sqlite import SQLite

    return SQLite(str(config.config_dir / "store.db"))
