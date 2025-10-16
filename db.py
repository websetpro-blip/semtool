from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
if not DATA_DIR.exists():
    DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "keyset.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  profile TEXT PRIMARY KEY,
  login TEXT,
  proxy TEXT,
  status TEXT DEFAULT 'ok',
  cooldown_until TEXT,
  last_ok TEXT,
  last_error TEXT,
  notes TEXT
);
"""

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.executescript(SCHEMA)
    return conn

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.commit()

def upsert_account(profile: str, login: str, proxy: Optional[str], status: str = "ok", notes: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO accounts(profile, login, proxy, status, notes)
            VALUES(?,?,?,?,?)
            ON CONFLICT(profile) DO UPDATE SET
              login=excluded.login,
              proxy=excluded.proxy,
              status=excluded.status,
              notes=excluded.notes
            """,
            (profile, login, proxy or "", status, notes),
        )
        conn.commit()

def update_status(profile: str, status: str, last_error: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE accounts SET status=?, last_error=? WHERE profile=?",
            (status, last_error, profile),
        )
        conn.commit()

def list_accounts(status_filter: Optional[Iterable[str]] = None) -> list[sqlite3.Row]:
    with get_conn() as conn:
        if status_filter:
            placeholders = ",".join("?" for _ in status_filter)
            cursor = conn.execute(
                f"SELECT * FROM accounts WHERE status IN ({placeholders}) ORDER BY profile",
                tuple(status_filter),
            )
        else:
            cursor = conn.execute("SELECT * FROM accounts ORDER BY profile")
        return cursor.fetchall()
