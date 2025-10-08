"""Summary storage extension for cc."""

import asyncio
import sqlite3
import time

from cogency.lib.ids import uuid7

from .db import DB


class Summaries:
    """Manages conversation summaries and message culling."""

    def __init__(self, db_path: str):
        """Initialize summary storage.

        Args:
            db_path: Path to database file.
        """
        self.db_path = db_path

        with DB.connect(self.db_path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS summaries (
                    summary_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT,
                    summary TEXT NOT NULL,
                    message_count INTEGER NOT NULL,
                    start_timestamp REAL NOT NULL,
                    end_timestamp REAL NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_summaries_conversation ON summaries(conversation_id, end_timestamp);
            """)

    async def save_summary(
        self,
        conversation_id: str,
        user_id: str,
        summary: str,
        message_count: int,
        start_ts: float,
        end_ts: float,
    ) -> str:
        summary_id = uuid7()

        def _sync_save():
            with DB.connect(self.db_path) as db:
                db.execute(
                    "INSERT INTO summaries (summary_id, conversation_id, user_id, summary, message_count, start_timestamp, end_timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        summary_id,
                        conversation_id,
                        user_id,
                        summary,
                        message_count,
                        start_ts,
                        end_ts,
                        time.time(),
                    ),
                )

        await asyncio.get_event_loop().run_in_executor(None, _sync_save)
        return summary_id

    async def load_summaries(self, conversation_id: str) -> list[dict]:
        def _sync_load():
            with DB.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                rows = db.execute(
                    "SELECT summary, message_count, start_timestamp, end_timestamp FROM summaries WHERE conversation_id = ? ORDER BY end_timestamp",
                    (conversation_id,),
                ).fetchall()
                return [
                    {
                        "summary": row["summary"],
                        "count": row["message_count"],
                        "start": row["start_timestamp"],
                        "end": row["end_timestamp"],
                    }
                    for row in rows
                ]

        return await asyncio.get_event_loop().run_in_executor(None, _sync_load)
