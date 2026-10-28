"""
memory.py - Persistent Spatial Memory Engine for EchoMap
Uses SQLite to store scans, object detections, spatial coordinates,
and user-taught corrections across application restarts.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

DB_PATH = Path("echomap.db")


def initialise(db_path: Optional[Path] = None) -> None:
    """Initializes tables for scans, detected objects, and user corrections."""
    with get_db(db_path) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scene TEXT NOT NULL,
                created_at TEXT NOT NULL,
                summary TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                confidence REAL NOT NULL,
                region_desc TEXT,
                FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_name TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                reference_object TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)
        db.commit()


@contextmanager
def get_db(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that reliably closes the SQLite connection on exit."""
    target_path = db_path or DB_PATH
    db = sqlite3.connect(target_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        db.close()


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a standalone connection (caller should close)."""
    target_path = db_path or DB_PATH
    db = sqlite3.connect(target_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def _ensure_initialised(db_path: Optional[Path] = None) -> None:
    """Helper to verify schema is in place."""
    initialise(db_path)


def save_scan(
    objects: List[Dict[str, Any]],
    scene: str = "desk",
    summary: str = "",
    db_path: Optional[Path] = None
) -> int:
    """Saves a new scan and all its identified objects to SQLite."""
    _ensure_initialised(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    with get_db(db_path) as db:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO scans (scene, created_at, summary) VALUES (?, ?, ?)",
            (scene, now_utc, summary)
        )
        scan_id = cursor.lastrowid

        for obj in objects:
            cursor.execute(
                """
                INSERT INTO objects (scan_id, name, x, y, confidence, region_desc)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_id,
                    obj.get("name", "").strip().lower(),
                    float(obj.get("x", 0.0)),
                    float(obj.get("y", 0.0)),
                    float(obj.get("confidence", 0.9)),
                    obj.get("region_desc", "")
                )
            )
        db.commit()
        return scan_id


def latest_scan(db_path: Optional[Path] = None) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """Retrieves the most recent scan record and its associated objects."""
    _ensure_initialised(db_path)
    with get_db(db_path) as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None
        scan = dict(row)
        cursor.execute(
            "SELECT id, name, x, y, confidence, region_desc FROM objects WHERE scan_id = ? ORDER BY id ASC",
            (scan["id"],)
        )
        objects = [dict(r) for r in cursor.fetchall()]
        return scan, objects


def previous_scan(db_path: Optional[Path] = None) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """Retrieves the scan immediately preceding the latest scan."""
    _ensure_initialised(db_path)
    with get_db(db_path) as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1 OFFSET 1")
        row = cursor.fetchone()
        if not row:
            return None
        scan = dict(row)
        cursor.execute(
            "SELECT id, name, x, y, confidence, region_desc FROM objects WHERE scan_id = ? ORDER BY id ASC",
            (scan["id"],)
        )
        objects = [dict(r) for r in cursor.fetchall()]
        return scan, objects


def get_scan_by_id(scan_id: int, db_path: Optional[Path] = None) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """Retrieves a specific scan by its primary key ID."""
    _ensure_initialised(db_path)
    with get_db(db_path) as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        scan = dict(row)
        cursor.execute(
            "SELECT id, name, x, y, confidence, region_desc FROM objects WHERE scan_id = ? ORDER BY id ASC",
            (scan["id"],)
        )
        objects = [dict(r) for r in cursor.fetchall()]
        return scan, objects


def get_all_scans(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns a list of all scan summaries ordered chronologically descending."""
    _ensure_initialised(db_path)
    with get_db(db_path) as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT s.id, s.scene, s.created_at, s.summary, COUNT(o.id) as object_count
            FROM scans s
            LEFT JOIN objects o ON s.id = o.scan_id
            GROUP BY s.id
            ORDER BY s.id DESC
        """)
        return [dict(r) for r in cursor.fetchall()]


def save_correction(
    object_name: str,
    relation_type: str,
    reference_object: str,
    note: str = "",
    db_path: Optional[Path] = None
) -> int:
    """
    Saves a user-taught correction or persistent spatial fact.
    Example: 'keys' are 'beside' 'phone'.
    """
    _ensure_initialised(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    with get_db(db_path) as db:
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO corrections (object_name, relation_type, reference_object, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                object_name.strip().lower(),
                relation_type.strip().lower(),
                reference_object.strip().lower(),
                note.strip(),
                now_utc
            )
        )
        db.commit()
        return cursor.lastrowid


def get_corrections(
    object_name: Optional[str] = None,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Retrieves all user corrections, optionally filtered for a specific object."""
    _ensure_initialised(db_path)
    with get_db(db_path) as db:
        cursor = db.cursor()
        if object_name:
            clean = object_name.strip().lower()
            cursor.execute(
                """
                SELECT * FROM corrections
                WHERE object_name = ? OR reference_object = ?
                ORDER BY id DESC
                """,
                (clean, clean)
            )
        else:
            cursor.execute("SELECT * FROM corrections ORDER BY id DESC")
        return [dict(r) for r in cursor.fetchall()]


def delete_correction(correction_id: int, db_path: Optional[Path] = None) -> None:
    """Deletes a correction by ID."""
    _ensure_initialised(db_path)
    with get_db(db_path) as db:
        db.execute("DELETE FROM corrections WHERE id = ?", (correction_id,))
        db.commit()


def clear_memory(db_path: Optional[Path] = None) -> None:
    """Clears all scans, objects, and corrections."""
    _ensure_initialised(db_path)
    with get_db(db_path) as db:
        db.execute("DELETE FROM corrections")
        db.execute("DELETE FROM objects")
        db.execute("DELETE FROM scans")
        db.commit()
