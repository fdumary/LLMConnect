import sqlite3
import os
import uuid
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class SavedChat:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "Untitled Chat"
    category: str = "Uncategorized"
    content: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class Database:
    def __init__(self, db_path=".llmconnect_data/database.sqlite"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        # Drop the old tasks table if we want a clean slate (optional, but good for the pivot)
        cursor.execute("DROP TABLE IF EXISTS tasks")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_chats (
                id TEXT PRIMARY KEY,
                title TEXT,
                category TEXT,
                content TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def save_chat(self, chat: SavedChat):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO saved_chats (id, title, category, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (chat.id, chat.title, chat.category, chat.content, chat.created_at),
        )
        self.conn.commit()

    def get_all_chats(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM saved_chats ORDER BY created_at DESC")
        rows = cursor.fetchall()
        chats = []
        for row in rows:
            chats.append(
                SavedChat(
                    id=row["id"],
                    title=row["title"],
                    category=row["category"],
                    content=row["content"],
                    created_at=row["created_at"],
                )
            )
        return chats
