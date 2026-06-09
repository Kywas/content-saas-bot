from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

import aiosqlite

from app.premium import extend_premium_until, is_premium_active


@dataclass
class UserRecord:
    user_id: int
    username: str | None
    first_name: str | None
    niche: str | None
    premium_until: str | None
    created_at: str


class Database:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    niche TEXT,
                    premium_until TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_daily (
                    user_id INTEGER NOT NULL,
                    usage_date TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, usage_date)
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def upsert_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
                """,
                (user_id, username, first_name, now),
            )
            await db.commit()

    async def get_user(self, user_id: int) -> UserRecord | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        return UserRecord(
            user_id=row["user_id"],
            username=row["username"],
            first_name=row["first_name"],
            niche=row["niche"],
            premium_until=row["premium_until"],
            created_at=row["created_at"],
        )

    async def set_niche(self, user_id: int, niche: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE users SET niche = ? WHERE user_id = ?",
                (niche.strip(), user_id),
            )
            await db.commit()

    async def is_premium(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if user is None:
            return False
        return is_premium_active(user.premium_until)

    async def grant_premium(self, user_id: int, days: int = 30) -> str:
        user = await self.get_user(user_id)
        until = extend_premium_until(user.premium_until if user else None, days)
        until_iso = until.isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE users SET premium_until = ? WHERE user_id = ?",
                (until_iso, user_id),
            )
            await db.commit()
        return until_iso

    async def record_payment(self, user_id: int, currency: str, amount: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO payments (user_id, currency, amount, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, currency, amount, now),
            )
            await db.commit()

    async def get_daily_usage(self, user_id: int) -> int:
        today = date.today().isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT count FROM usage_daily WHERE user_id = ? AND usage_date = ?",
                (user_id, today),
            ) as cursor:
                row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def increment_usage(self, user_id: int) -> int:
        today = date.today().isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO usage_daily (user_id, usage_date, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, usage_date) DO UPDATE SET
                    count = count + 1
                """,
                (user_id, today),
            )
            await db.commit()
            async with db.execute(
                "SELECT count FROM usage_daily WHERE user_id = ? AND usage_date = ?",
                (user_id, today),
            ) as cursor:
                row = await cursor.fetchone()
        return int(row[0]) if row else 1

    async def get_stats(self) -> dict[str, int]:
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total_users = (await cursor.fetchone())[0]
            async with db.execute(
                """
                SELECT COUNT(*) FROM users
                WHERE premium_until IS NOT NULL AND premium_until > ?
                """,
                (datetime.now(timezone.utc).isoformat(),),
            ) as cursor:
                active_premium = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM payments") as cursor:
                total_payments = (await cursor.fetchone())[0]
            async with db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments") as cursor:
                total_revenue = (await cursor.fetchone())[0]
            today = date.today().isoformat()
            async with db.execute(
                "SELECT COALESCE(SUM(count), 0) FROM usage_daily WHERE usage_date = ?",
                (today,),
            ) as cursor:
                today_requests = (await cursor.fetchone())[0]
        return {
            "total_users": int(total_users),
            "active_premium": int(active_premium),
            "total_payments": int(total_payments),
            "total_revenue": int(total_revenue),
            "today_requests": int(today_requests),
        }
