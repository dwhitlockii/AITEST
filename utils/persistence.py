import aiosqlite
import os
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

SCHEMA_VERSION = 1


class PersistenceManager:
    def __init__(
        self,
        db_path: str = "data/agent_system.db",
        retention_days: Optional[int] = None,
    ):
        self.db_path = db_path
        self._initialized = False
        self.retention_days = retention_days  # None = unlimited
        self._lock = asyncio.Lock()  # Prevent concurrent database access

    async def initialize(self):
        async with self._lock:
            if not os.path.exists(os.path.dirname(self.db_path)):
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            async with aiosqlite.connect(self.db_path, timeout=30.0) as db:
                # Schema versioning
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY
                    )
                """
                )
                cursor = await db.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                )
                version_row = await cursor.fetchone()
                if not version_row:
                    await db.execute(
                        "INSERT INTO schema_version (version) VALUES (?)",
                        (SCHEMA_VERSION,),
                    )
                # Main tables
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        agent TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        value TEXT NOT NULL
                    )
                """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        agent TEXT NOT NULL,
                        summary TEXT,
                        issues TEXT
                    )
                """
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS remediation (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        agent TEXT NOT NULL,
                        action TEXT NOT NULL,
                        result TEXT NOT NULL
                    )
                """
                )
                await db.commit()
            self._initialized = True

    async def insert_metric(
        self, timestamp: str, agent: str, metric_type: str, value: str
    ):
        await self._ensure_initialized()
        async with self._lock:
            for attempt in range(3):  # Retry up to 3 times
                try:
                    async with aiosqlite.connect(self.db_path, timeout=10.0) as db:
                        await db.execute(
                            "INSERT INTO metrics (timestamp, agent, metric_type, value) VALUES (?, ?, ?, ?)",
                            (timestamp, agent, metric_type, value),
                        )
                        await db.commit()
                        return
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        print(f"Warning: Failed to insert metric after 3 attempts: {e}")
                        return  # Don't raise, just log and continue
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

    async def insert_analysis(
        self, timestamp: str, agent: str, summary: str, issues: str
    ):
        await self._ensure_initialized()
        async with self._lock:
            for attempt in range(3):  # Retry up to 3 times
                try:
                    async with aiosqlite.connect(self.db_path, timeout=10.0) as db:
                        await db.execute(
                            "INSERT INTO analysis (timestamp, agent, summary, issues) VALUES (?, ?, ?, ?)",
                            (timestamp, agent, summary, issues),
                        )
                        await db.commit()
                        return
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        print(
                            f"Warning: Failed to insert analysis after 3 attempts: {e}"
                        )
                        return  # Don't raise, just log and continue
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

    async def insert_remediation(
        self, timestamp: str, agent: str, action: str, result: str
    ):
        await self._ensure_initialized()
        async with self._lock:
            for attempt in range(3):  # Retry up to 3 times
                try:
                    async with aiosqlite.connect(self.db_path, timeout=10.0) as db:
                        await db.execute(
                            "INSERT INTO remediation (timestamp, agent, action, result) VALUES (?, ?, ?, ?)",
                            (timestamp, agent, action, result),
                        )
                        await db.commit()
                        return
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        print(
                            f"Warning: Failed to insert remediation after 3 attempts: {e}"
                        )
                        return  # Don't raise, just log and continue
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

    async def query_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        await self._ensure_initialized()
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path, timeout=10.0) as db:
                    async with db.execute(
                        "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?",
                        (limit,),
                    ) as cursor:
                        rows = await cursor.fetchall()
                        return [
                            dict(zip([column[0] for column in cursor.description], row))
                            for row in rows
                        ]
            except Exception as e:
                print(f"Warning: Failed to query metrics: {e}")
                return []

    async def query_analysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        await self._ensure_initialized()
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path, timeout=10.0) as db:
                    async with db.execute(
                        "SELECT * FROM analysis ORDER BY timestamp DESC LIMIT ?",
                        (limit,),
                    ) as cursor:
                        rows = await cursor.fetchall()
                        return [
                            dict(zip([column[0] for column in cursor.description], row))
                            for row in rows
                        ]
            except Exception as e:
                print(f"Warning: Failed to query analysis: {e}")
                return []

    async def query_remediation(self, limit: int = 100) -> List[Dict[str, Any]]:
        await self._ensure_initialized()
        async with self._lock:
            try:
                async with aiosqlite.connect(self.db_path, timeout=10.0) as db:
                    async with db.execute(
                        "SELECT * FROM remediation ORDER BY timestamp DESC LIMIT ?",
                        (limit,),
                    ) as cursor:
                        rows = await cursor.fetchall()
                        return [
                            dict(zip([column[0] for column in cursor.description], row))
                            for row in rows
                        ]
            except Exception as e:
                print(f"Warning: Failed to query remediation: {e}")
                return []

    async def cleanup_old_records(self):
        """Delete records older than retention_days, if set."""
        if self.retention_days is None:
            return
        await self._ensure_initialized()
        async with self._lock:
            try:
                cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
                cutoff_str = cutoff.isoformat()
                async with aiosqlite.connect(self.db_path, timeout=30.0) as db:
                    for table in ("metrics", "analysis", "remediation"):
                        await db.execute(
                            f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_str,)
                        )
                    await db.commit()
            except Exception as e:
                print(f"Warning: Failed to cleanup old records: {e}")

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()
