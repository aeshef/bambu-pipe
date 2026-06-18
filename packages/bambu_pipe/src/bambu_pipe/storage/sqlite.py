"""SQLite-backed job store."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from bambu_pipe.models.job import PrintJob


class SQLiteJobStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._initialized = False

    async def _ensure_schema(self) -> None:
        if self._initialized:
            return
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._database_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            await db.commit()
        self._initialized = True

    async def save(self, job: PrintJob) -> None:
        await self._ensure_schema()
        async with aiosqlite.connect(self._database_path) as db:
            await db.execute(
                """
                INSERT INTO jobs (id, created_at, updated_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    job.id,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.model_dump_json(),
                ),
            )
            await db.commit()

    async def get(self, job_id: str) -> PrintJob | None:
        await self._ensure_schema()
        async with aiosqlite.connect(self._database_path) as db:
            cursor = await db.execute("SELECT payload FROM jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return PrintJob.model_validate_json(row[0])

    async def list(self) -> list[PrintJob]:
        await self._ensure_schema()
        async with aiosqlite.connect(self._database_path) as db:
            cursor = await db.execute("SELECT payload FROM jobs ORDER BY created_at DESC")
            rows = await cursor.fetchall()
        return [PrintJob.model_validate_json(row[0]) for row in rows]
