"""
SQLite database for tracking documentation evolution history.

Tracks all documentation updates, soul snapshots, and evolution events
for audit and diagnostic purposes.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class EvolutionRecord:
    """Represents a single evolution event."""
    id: Optional[int] = None
    timestamp: Optional[str] = None
    commit_hash: str = ""
    commit_message: str = ""
    changed_files: List[str] = None
    doc_targets: List[str] = None
    is_significant: bool = False
    update_mode: str = "async"
    triggers_soul: bool = False
    soul_snapshot_created: bool = False
    docs_updated: List[str] = None
    status: str = "pending"
    error_message: Optional[str] = None
    branch: str = "main"
    agent_tag: str = "evolution-system"

    def __post_init__(self):
        if self.changed_files is None:
            self.changed_files = []
        if self.doc_targets is None:
            self.doc_targets = []
        if self.docs_updated is None:
            self.docs_updated = []


class EvolutionDatabase:
    """Manages the evolution tracking database."""

    DEFAULT_DB_PATH = "ai-env/evolution.db"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Create the database and tables if they don't exist."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    commit_hash TEXT UNIQUE,
                    commit_message TEXT,
                    changed_files TEXT,
                    doc_targets TEXT,
                    is_significant BOOLEAN,
                    update_mode TEXT,
                    triggers_soul BOOLEAN DEFAULT 0,
                    soul_snapshot_created BOOLEAN,
                    docs_updated TEXT,
                    status TEXT,
                    error_message TEXT,
                    branch TEXT,
                    agent_tag TEXT
                )
            """)

            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON evolution_log(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_commit_hash ON evolution_log(commit_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON evolution_log(status)
            """)

            conn.commit()

            # Add triggers_soul column if it doesn't exist (migration)
            try:
                conn.execute("ALTER TABLE evolution_log ADD COLUMN triggers_soul BOOLEAN DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def log_evolution(self, record: EvolutionRecord) -> int:
        """
        Log a new evolution event.

        Args:
            record: The evolution record to store

        Returns:
            The ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO evolution_log (
                    commit_hash, commit_message, changed_files, doc_targets,
                    is_significant, update_mode, triggers_soul, soul_snapshot_created, docs_updated,
                    status, error_message, branch, agent_tag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.commit_hash,
                record.commit_message,
                json.dumps(record.changed_files),
                json.dumps(record.doc_targets),
                record.is_significant,
                record.update_mode,
                record.triggers_soul,
                record.soul_snapshot_created,
                json.dumps(record.docs_updated),
                record.status,
                record.error_message,
                record.branch,
                record.agent_tag
            ))
            conn.commit()
            return cursor.lastrowid

    def update_status(self, commit_hash: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        Update the status of an evolution record.

        Args:
            commit_hash: The commit hash to update
            status: New status ('pending', 'running', 'completed', 'failed')
            error_message: Optional error message

        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE evolution_log
                SET status = ?, error_message = ?
                WHERE commit_hash = ?
            """, (status, error_message, commit_hash))
            conn.commit()
            return cursor.rowcount > 0

    def get_record(self, commit_hash: str) -> Optional[EvolutionRecord]:
        """Get a single evolution record by commit hash."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM evolution_log WHERE commit_hash = ?
            """, (commit_hash,))
            row = cursor.fetchone()

            if row:
                return self._row_to_record(row)
            return None

    def get_recent_records(self, limit: int = 10) -> List[EvolutionRecord]:
        """Get the most recent evolution records."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM evolution_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_pending_async_updates(self) -> List[EvolutionRecord]:
        """Get all pending async updates that need to be processed."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM evolution_log
                WHERE update_mode = 'async' AND status = 'pending'
                ORDER BY timestamp ASC
            """)
            return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get evolution system statistics."""
        with self._get_connection() as conn:
            stats = {}

            # Total records
            cursor = conn.execute("SELECT COUNT(*) FROM evolution_log")
            stats['total_records'] = cursor.fetchone()[0]

            # Records by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) FROM evolution_log GROUP BY status
            """)
            stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}

            # Significant changes
            cursor = conn.execute("""
                SELECT COUNT(*) FROM evolution_log WHERE is_significant = 1
            """)
            stats['significant_changes'] = cursor.fetchone()[0]

            # Soul snapshots
            cursor = conn.execute("""
                SELECT COUNT(*) FROM evolution_log WHERE soul_snapshot_created = 1
            """)
            stats['soul_snapshots'] = cursor.fetchone()[0]

            # Recent activity (last 24 hours)
            cursor = conn.execute("""
                SELECT COUNT(*) FROM evolution_log
                WHERE timestamp > datetime('now', '-1 day')
            """)
            stats['last_24h'] = cursor.fetchone()[0]

            return stats

    def _row_to_record(self, row: sqlite3.Row) -> EvolutionRecord:
        """Convert a database row to an EvolutionRecord."""
        # Handle both old schema (13 cols) and new schema (14 cols with triggers_soul)
        if len(row) >= 14:
            return EvolutionRecord(
                id=row[0],
                timestamp=row[1],
                commit_hash=row[2],
                commit_message=row[3],
                changed_files=json.loads(row[4]) if row[4] else [],
                doc_targets=json.loads(row[5]) if row[5] else [],
                is_significant=bool(row[6]),
                update_mode=row[7],
                triggers_soul=bool(row[8]),
                soul_snapshot_created=bool(row[9]),
                docs_updated=json.loads(row[10]) if row[10] else [],
                status=row[11],
                error_message=row[12],
                branch=row[13],
                agent_tag=row[14] if len(row) > 14 else "evolution-system"
            )
        else:
            # Legacy schema without triggers_soul column
            return EvolutionRecord(
                id=row[0],
                timestamp=row[1],
                commit_hash=row[2],
                commit_message=row[3],
                changed_files=json.loads(row[4]) if row[4] else [],
                doc_targets=json.loads(row[5]) if row[5] else [],
                is_significant=bool(row[6]),
                update_mode=row[7],
                triggers_soul=False,
                soul_snapshot_created=bool(row[8]),
                docs_updated=json.loads(row[9]) if row[9] else [],
                status=row[10],
                error_message=row[11],
                branch=row[12],
                agent_tag=row[13] if len(row) > 13 else "evolution-system"
            )

    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Remove records older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of records deleted
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM evolution_log
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            conn.commit()
            return cursor.rowcount

    def record_handoff(self, commit_hash: str, commit_message: str, snapshot_text: str = "") -> int:
        """
        Record a handoff event in the evolution log.

        Args:
            commit_hash: The git commit hash
            commit_message: The commit message
            snapshot_text: Optional soul snapshot text

        Returns:
            The ID of the inserted record
        """
        record = EvolutionRecord(
            commit_hash=commit_hash,
            commit_message=commit_message,
            changed_files=[],
            doc_targets=["soul/identity.md"],
            is_significant=True,
            update_mode="sync",
            soul_snapshot_created=bool(snapshot_text),
            docs_updated=["ai-env/soul/identity.md"] if snapshot_text else [],
            status="completed",
            branch="main",
            agent_tag="handoff-script"
        )
        return self.log_evolution(record)

    def get_last_handoff(self) -> Optional[EvolutionRecord]:
        """Get the most recent handoff record."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM evolution_log
                WHERE agent_tag = 'handoff-script'
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None


# Global database instance
_db_instance: Optional[EvolutionDatabase] = None


def get_database() -> EvolutionDatabase:
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = EvolutionDatabase()
    return _db_instance
