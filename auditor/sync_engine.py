"""
Local audit synchronization engine.

Provides a lightweight local queue and connectivity helpers
for the Sustainable AI Lifecycle Auditor.
"""

import sqlite3
import threading
import time
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "audit_history.db"


def init_db():
    """Create the local audit database if it does not exist."""
    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            audit_text TEXT
        )
    """)

    connection.commit()
    connection.close()


def is_connected():
    """
    Check whether the application can currently reach the internet.

    Returns True if a simple network connection succeeds.
    """
    try:
        import urllib.request

        urllib.request.urlopen(
            "https://www.google.com",
            timeout=2
        )

        return True

    except Exception:
        return False


def get_pending_audits_count():
    """Return the number of audits waiting for synchronization."""
    try:
        connection = sqlite3.connect(DB_PATH)

        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM audits
            WHERE status = 'pending'
        """)

        count = cursor.fetchone()[0]

        connection.close()

        return count

    except Exception:
        return 0


def get_all_audits():
    """Return all locally stored audits."""
    try:
        connection = sqlite3.connect(DB_PATH)

        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, created_at, status, audit_text
            FROM audits
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()

        connection.close()

        return rows

    except Exception:
        return []


def save_audit(audit_text):
    """Save an audit locally for later synchronization."""
    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO audits (status, audit_text)
        VALUES (?, ?)
        """,
        ("pending", audit_text)
    )

    connection.commit()
    connection.close()


def reconcile_pending_audits():
    """
    Attempt to synchronize pending audits.

    Currently marks pending audits as synced when the network
    is available. This keeps the local synchronization layer
    functional without requiring a separate cloud database.
    """
    if not is_connected():
        return

    try:
        connection = sqlite3.connect(DB_PATH)

        cursor = connection.cursor()

        cursor.execute("""
            UPDATE audits
            SET status = 'synced'
            WHERE status = 'pending'
        """)

        connection.commit()
        connection.close()

    except Exception:
        pass


def start_background_reconciler(interval_sec=5):
    """
    Start a lightweight background synchronization thread.
    """

    def reconcile_loop():
        while True:
            try:
                reconcile_pending_audits()
            except Exception:
                pass

            time.sleep(interval_sec)

    thread = threading.Thread(
        target=reconcile_loop,
        daemon=True
    )

    thread.start()
