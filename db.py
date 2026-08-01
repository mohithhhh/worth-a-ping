import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


DB_PATH = "messages.db"


def _get_connection():
    """Get a database connection and ensure schema exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn):
    """Create the messages table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            subject TEXT,
            body TEXT NOT NULL,
            received_at TEXT NOT NULL,
            urgent INTEGER NOT NULL DEFAULT 0,
            reason TEXT,
            alerted INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversation_id 
        ON messages(conversation_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sender 
        ON messages(sender)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_received_at 
        ON messages(received_at DESC)
    """)
    conn.commit()


def log_message(
    conversation_id: str,
    sender: str,
    body: str,
    subject: Optional[str] = None,
    urgent: bool = False,
    reason: Optional[str] = None,
) -> int:
    """
    Log an inbound message to the database.
    
    Returns the message ID.
    """
    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT INTO messages (conversation_id, sender, subject, body, received_at, urgent, reason, alerted)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            conversation_id,
            sender,
            subject,
            body,
            datetime.utcnow().isoformat(),
            1 if urgent else 0,
            reason,
        ),
    )
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return message_id


def get_recent_context(conversation_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve recent messages from the same conversation for context.
    
    Returns a list of message dicts, ordered newest to oldest.
    """
    conn = _get_connection()
    cursor = conn.execute(
        """
        SELECT sender, subject, body, received_at, urgent, reason
        FROM messages
        WHERE conversation_id = ?
        ORDER BY received_at DESC
        LIMIT ?
        """,
        (conversation_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def mark_alerted(message_id: int):
    """Mark a message as having triggered an alert."""
    conn = _get_connection()
    conn.execute(
        "UPDATE messages SET alerted = 1 WHERE id = ?",
        (message_id,),
    )
    conn.commit()
    conn.close()
