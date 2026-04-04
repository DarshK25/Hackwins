"""
Persistent Memory Store - Works with or without Redis
Uses file-based SQLite storage as fallback when Redis is unavailable
"""

import json
import os
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from threading import Lock
import sqlite3

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PersistentMemory:
    """
    Persistent memory that works WITHOUT Redis.
    Uses SQLite for cross-process persistence.
    Falls back gracefully when Redis is available.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_path = Path(__file__).resolve().parents[3] / "data"
            base_path.mkdir(exist_ok=True)
            db_path = str(base_path / "moneyops_memory.db")

        self._db_path = db_path
        self._lock = Lock()
        self._redis_fallback = True
        self._redis_client = None
        self._init_db()
        logger.info({"event": "persistent_memory_initialized", "db_path": db_path})

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS memory (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at REAL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory(expires_at);
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        intent TEXT,
                        metadata TEXT,
                        created_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_conv_session ON conversation_history(session_id);
                    CREATE TABLE IF NOT EXISTS agent_knowledge (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        org_id TEXT NOT NULL,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        source TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        UNIQUE(org_id, category, key)
                    );
                    CREATE INDEX IF NOT EXISTS idx_knowledge_org ON agent_knowledge(org_id);
                """)
                conn.commit()
            finally:
                conn.close()

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO memory (key, value, expires_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        expires_at = excluded.expires_at,
                        updated_at = excluded.updated_at
                """,
                    (key, json.dumps(value), expires_at, time.time(), time.time()),
                )
                conn.commit()
                return True
            except Exception as e:
                logger.error({"event": "memory_set_error", "key": key, "error": str(e)})
                return False
            finally:
                conn.close()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    """
                    SELECT value, expires_at FROM memory WHERE key = ?
                """,
                    (key,),
                ).fetchone()

                if not row:
                    return None

                if row["expires_at"] and row["expires_at"] < time.time():
                    conn.execute("DELETE FROM memory WHERE key = ?", (key,))
                    conn.commit()
                    return None

                return json.loads(row["value"])
            except Exception as e:
                logger.error({"event": "memory_get_error", "key": key, "error": str(e)})
                return None
            finally:
                conn.close()

    def delete(self, key: str) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM memory WHERE key = ?", (key,))
                conn.commit()
                return True
            except Exception as e:
                logger.error(
                    {"event": "memory_delete_error", "key": key, "error": str(e)}
                )
                return False
            finally:
                conn.close()

    def add_conversation_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO conversation_history 
                    (session_id, role, content, intent, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        role,
                        content,
                        intent,
                        json.dumps(metadata or {}),
                        time.time(),
                    ),
                )
                conn.commit()
                return True
            except Exception as e:
                logger.error(
                    {
                        "event": "conversation_add_error",
                        "session_id": session_id,
                        "error": str(e),
                    }
                )
                return False
            finally:
                conn.close()

    def get_conversation_history(
        self, session_id: str, max_turns: int = 20
    ) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute(
                    """
                    SELECT role, content, intent, metadata, created_at
                    FROM conversation_history
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (session_id, max_turns),
                ).fetchall()

                history = []
                for row in reversed(rows):
                    history.append(
                        {
                            "role": row["role"],
                            "content": row["content"],
                            "intent": row["intent"],
                            "metadata": json.loads(row["metadata"])
                            if row["metadata"]
                            else {},
                            "created_at": row["created_at"],
                        }
                    )
                return history
            except Exception as e:
                logger.error(
                    {
                        "event": "conversation_get_error",
                        "session_id": session_id,
                        "error": str(e),
                    }
                )
                return []
            finally:
                conn.close()

    def store_knowledge(
        self,
        org_id: str,
        category: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: Optional[str] = None,
    ) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO agent_knowledge 
                    (org_id, category, key, value, confidence, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(org_id, category, key) DO UPDATE SET
                        value = excluded.value,
                        confidence = excluded.confidence,
                        source = excluded.source,
                        updated_at = excluded.updated_at
                """,
                    (
                        org_id,
                        category,
                        key,
                        json.dumps(value),
                        confidence,
                        source,
                        time.time(),
                        time.time(),
                    ),
                )
                conn.commit()
                return True
            except Exception as e:
                logger.error(
                    {
                        "event": "knowledge_store_error",
                        "org_id": org_id,
                        "error": str(e),
                    }
                )
                return False
            finally:
                conn.close()

    def get_knowledge(
        self, org_id: str, category: Optional[str] = None
    ) -> Dict[str, Any]:
        with self._lock:
            conn = self._get_connection()
            try:
                if category:
                    rows = conn.execute(
                        """
                        SELECT category, key, value, confidence, source
                        FROM agent_knowledge
                        WHERE org_id = ? AND category = ?
                        ORDER BY confidence DESC
                    """,
                        (org_id, category),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT category, key, value, confidence, source
                        FROM agent_knowledge
                        WHERE org_id = ?
                        ORDER BY category, confidence DESC
                    """,
                        (org_id,),
                    ).fetchall()

                result = {}
                for row in rows:
                    cat = row["category"]
                    if cat not in result:
                        result[cat] = []
                    result[cat].append(
                        {
                            "key": row["key"],
                            "value": json.loads(row["value"]),
                            "confidence": row["confidence"],
                            "source": row["source"],
                        }
                    )
                return result
            except Exception as e:
                logger.error(
                    {"event": "knowledge_get_error", "org_id": org_id, "error": str(e)}
                )
                return {}
            finally:
                conn.close()

    def cleanup_expired(self) -> int:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    DELETE FROM memory WHERE expires_at < ?
                """,
                    (time.time(),),
                )
                conn.commit()
                count = cursor.rowcount
                if count > 0:
                    logger.info({"event": "memory_cleanup", "deleted": count})
                return count
            except Exception as e:
                logger.error({"event": "memory_cleanup_error", "error": str(e)})
                return 0
            finally:
                conn.close()


persistent_memory = PersistentMemory()
