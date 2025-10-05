"""Conversation listing utilities for cogency-code."""

import sqlite3
import time
from pathlib import Path


async def list_conversations(base_dir: str = None, limit: int = 10) -> list[dict]:
    """List recent conversations with first message preview."""
    if base_dir:
        db_path = Path(base_dir) / ".cogency" / "store.db"
    else:
        db_path = Path(".cogency/store.db")

    if not db_path.exists():
        return []

    def _sync_query():
        with sqlite3.connect(db_path) as db:
            # Get first user message for each conversation
            cursor = db.execute(
                """
                SELECT
                    c1.conversation_id,
                    c1.user_id,
                    c1.content as first_message,
                    c1.timestamp,
                    COUNT(c2.timestamp) as message_count
                FROM messages c1
                LEFT JOIN messages c2 ON c1.conversation_id = c2.conversation_id
                WHERE c1.type = 'user' AND c1.timestamp = (
                    SELECT MIN(timestamp)
                    FROM messages
                    WHERE conversation_id = c1.conversation_id AND type = 'user'
                )
                GROUP BY c1.conversation_id, c1.user_id, c1.content, c1.timestamp
                ORDER BY c1.timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

            results = []
            for row in cursor.fetchall():
                conversation_id, user_id, first_msg, timestamp, count = row

                # Truncate first message for display
                preview = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg

                results.append(
                    {
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "preview": preview,
                        "timestamp": timestamp,
                        "message_count": count,
                        "time_ago": _format_time_ago(timestamp),
                    }
                )

            return results

    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, _sync_query)


def get_last_conversation(base_dir: str = None) -> str | None:
    """Get most recent conversation ID for current project."""
    if base_dir:
        db_path = Path(base_dir) / ".cogency" / "store.db"
    else:
        db_path = Path(".cogency/store.db")

    if not db_path.exists():
        return None

    with sqlite3.connect(db_path) as db:
        cursor = db.execute(
            """
            SELECT conversation_id
            FROM messages
            ORDER BY timestamp DESC
            LIMIT 1
        """
        )
        row = cursor.fetchone()
        return row[0] if row else None


def _format_time_ago(timestamp: float) -> str:
    """Format timestamp as relative time."""
    seconds = time.time() - timestamp

    if seconds < 3600:  # Less than 1 hour
        minutes = int(seconds / 60)
        return f"{minutes}m ago" if minutes > 0 else "Just now"
    if seconds < 86400:  # Less than 1 day
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    if seconds < 604800:  # Less than 1 week
        days = int(seconds / 86400)
        return f"{days}d ago"
    weeks = int(seconds / 604800)
    return f"{weeks}w ago"
