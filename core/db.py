import aiosqlite
import os

class Database:
    def __init__(self, db_path="data/history.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reply_history (
                    post_id TEXT PRIMARY KEY,
                    reply_content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def is_replied(self, post_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM reply_history WHERE post_id = ?", (post_id,)) as cursor:
                return await cursor.fetchone() is not None

    async def add_reply(self, post_id: str, reply_content: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO reply_history (post_id, reply_content) VALUES (?, ?)",
                (post_id, reply_content)
            )
            await db.commit()
