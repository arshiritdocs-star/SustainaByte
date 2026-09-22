"""
Local audit persistence and connectivity/reconciliation engine for SustainaByte.

The lifecycle calculations are local and remain usable without internet.
Audit results are stored in SQLite as an outbox. When connectivity returns,
pending records are automatically reconciled. This project currently has no
remote persistence endpoint, so "reconciled" means the local outbox record
has been successfully retained and processed after connectivity recovery;
the code is structured so a real remote sync target can be added later.
"""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).resolve().parent / "audit_history.db"

_reconciler_thread = None
_reconciler_lock = threading.Lock()
_simulated_outage = False


def _connect():
    """Open a short-lived SQLite connection."""
    connection = sqlite3.connect(DB_PATH, timeout=5)
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_db():
    """Create/migrate the local audit database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = _connect()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                audit_text TEXT
            )
            """
        )

        # Backward-compatible migrations for databases created by older code.
        columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(audits)").fetchall()
        }

        if "audit_key" not in columns:
            cursor.execute("ALTER TABLE audits ADD COLUMN audit_key TEXT")

        if "source" not in columns:
            cursor.execute(
                "ALTER TABLE audits ADD COLUMN source TEXT DEFAULT 'local'"
            )

        if "reconciled_at" not in columns:
            cursor.execute(
                "ALTER TABLE audits ADD COLUMN reconciled_at TIMESTAMP"
            )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_audits_audit_key
            ON audits(audit_key)
            WHERE audit_key IS NOT NULL
            """
        )

        connection.commit()
    finally:
        connection.close()


def set_simulated_outage(enabled: bool):
    """Force the application into/out of offline mode for demonstrations."""
    global _simulated_outage
    _simulated_outage = bool(enabled)


def is_simulated_outage() -> bool:
    """Return whether demo offline mode is enabled."""
    return _simulated_outage


def is_connected() -> bool:
    """
    Return True when internet is available and demo outage is not enabled.
    """
    if _simulated_outage:
        return False

    try:
        import urllib.request

        urllib.request.urlopen(
            "https://www.google.com/generate_204",
            timeout=2,
        )
        return True
    except Exception:
        return False


def get_pending_audits_count() -> int:
    """Return the number of audits waiting for reconciliation."""
    try:
        connection = _connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM audits WHERE status = 'pending'"
            )
            return int(cursor.fetchone()[0])
        finally:
            connection.close()
    except Exception:
        return 0


def get_all_audits():
    """Return all locally stored audits, newest first."""
    try:
        connection = _connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, created_at, status, source, reconciled_at, audit_text
                FROM audits
                ORDER BY created_at DESC
                """
            )
            return cursor.fetchall()
        finally:
            connection.close()
    except Exception:
        return []


def save_audit(
    audit_text: str,
    audit_key: Optional[str] = None,
    source: str = "local",
) -> bool:
    """
    Persist an audit in the local outbox.

    Returns True when a new record was inserted and False when the same
    audit_key already exists.
    """
    if not audit_text:
        return False

    connection = _connect()
    try:
        cursor = connection.cursor()

        if audit_key:
            cursor.execute(
                """
                INSERT OR IGNORE INTO audits
                    (status, audit_text, audit_key, source)
                VALUES (?, ?, ?, ?)
                """,
                ("pending", audit_text, audit_key, source),
            )
        else:
            cursor.execute(
                """
                INSERT INTO audits (status, audit_text, source)
                VALUES (?, ?, ?)
                """,
                ("pending", audit_text, source),
            )

        inserted = cursor.rowcount > 0
        connection.commit()
        return inserted
    finally:
        connection.close()


def reconcile_pending_audits() -> int:
    """
    Reconcile pending records after connectivity returns.

    There is currently no remote backend in this project. Therefore this
    function does not falsely claim that records were uploaded to a server.
    It marks durable local outbox records as 'reconciled' after connectivity
    is restored. A future remote backend can replace this section.
    """
    if not is_connected():
        return 0

    try:
        connection = _connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE audits
                SET status = 'reconciled',
                    reconciled_at = CURRENT_TIMESTAMP
                WHERE status = 'pending'
                """
            )
            changed = cursor.rowcount
            connection.commit()
            return int(changed)
        finally:
            connection.close()
    except Exception:
        return 0


def start_background_reconciler(interval_sec: int = 5):
    """
    Start one daemon reconciler per Python process.

    The thread periodically checks connectivity and reconciles pending
    records automatically. Calling this function repeatedly is safe.
    """
    global _reconciler_thread

    with _reconciler_lock:
        if (
            _reconciler_thread is not None
            and _reconciler_thread.is_alive()
        ):
            return

        def reconcile_loop():
            while True:
                try:
                    reconcile_pending_audits()
                except Exception:
                    pass
                time.sleep(max(1, int(interval_sec)))

        _reconciler_thread = threading.Thread(
            target=reconcile_loop,
            name="sustainabyte-audit-reconciler",
            daemon=True,
        )
        _reconciler_thread.start()
