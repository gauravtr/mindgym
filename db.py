"""Storage for MindGym accounts and practice history.

Uses Postgres when a connection URL is configured (Streamlit secret / env var
DATABASE_URL), otherwise a local SQLite file. On Streamlit Community Cloud the
SQLite file is wiped whenever the app restarts or is redeployed, so set
DATABASE_URL for permanent storage.
"""
import hashlib
import hmac
import os
import secrets as _secrets
import sqlite3
from datetime import datetime, timezone

import pandas as pd

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id {pk},
        username TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TEXT NOT NULL,
        daily_goal INTEGER DEFAULT 30
    )""",
    """CREATE TABLE IF NOT EXISTS math_attempts (
        id {pk},
        user_id INTEGER NOT NULL,
        ts TEXT NOT NULL,
        category TEXT, level TEXT, question TEXT, answer TEXT, given TEXT,
        correct INTEGER, seconds REAL
    )""",
    """CREATE TABLE IF NOT EXISTS memory_attempts (
        id {pk},
        user_id INTEGER NOT NULL,
        ts TEXT NOT NULL,
        length INTEGER, direction TEXT, style TEXT, correct INTEGER, digits_right INTEGER
    )""",
    "CREATE INDEX IF NOT EXISTS ix_math_user ON math_attempts(user_id, ts)",
    "CREATE INDEX IF NOT EXISTS ix_mem_user ON memory_attempts(user_id, ts)",
]


class Store:
    def __init__(self, url=None, sqlite_path="mindgym.db"):
        self.url = url
        if url and url.startswith(("postgres://", "postgresql://")):
            import psycopg2  # only needed when Postgres is configured
            self.kind = "postgres"
            self._connect = lambda: psycopg2.connect(url)
            self.ph, pk = "%s", "SERIAL PRIMARY KEY"
        else:
            self.kind = "sqlite"
            self._connect = lambda: sqlite3.connect(sqlite_path)
            self.ph, pk = "?", "INTEGER PRIMARY KEY AUTOINCREMENT"
        with self._conn() as (con, cur):
            for stmt in SCHEMA:
                cur.execute(stmt.format(pk=pk))

    @property
    def permanent(self):
        return self.kind == "postgres"

    # --- low-level helpers
    class _Ctx:
        def __init__(self, store):
            self.store = store

        def __enter__(self):
            self.con = self.store._connect()
            self.cur = self.con.cursor()
            return self.con, self.cur

        def __exit__(self, exc_type, *a):
            if exc_type is None:
                self.con.commit()
            self.con.close()
            return False

    def _conn(self):
        return Store._Ctx(self)

    def _q(self, sql):
        return sql.replace("?", self.ph)

    # --- users
    @staticmethod
    def _hash(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()

    def create_user(self, username, password):
        """Returns (user_dict, error_message)."""
        username = username.strip().lower()
        if not (3 <= len(username) <= 30) or not all(c.isalnum() or c in "_.-" for c in username):
            return None, "Username must be 3–30 characters: letters, numbers, _ . -"
        if len(password) < 6:
            return None, "Password must be at least 6 characters."
        if self.get_user(username):
            return None, "That username is taken."
        salt = _secrets.token_hex(16)
        with self._conn() as (con, cur):
            cur.execute(self._q("INSERT INTO users (username, pw_hash, salt, created_at) VALUES (?, ?, ?, ?)"),
                        (username, self._hash(password, salt), salt, _now()))
        return self.get_user(username), None

    def get_user(self, username):
        with self._conn() as (con, cur):
            cur.execute(self._q("SELECT id, username, pw_hash, salt, created_at, daily_goal FROM users WHERE username = ?"),
                        (username.strip().lower(),))
            row = cur.fetchone()
        if not row:
            return None
        return dict(zip(["id", "username", "pw_hash", "salt", "created_at", "daily_goal"], row))

    def login(self, username, password):
        u = self.get_user(username)
        if not u or not hmac.compare_digest(u["pw_hash"], self._hash(password, u["salt"])):
            return None
        return u

    def set_goal(self, user_id, goal):
        with self._conn() as (con, cur):
            cur.execute(self._q("UPDATE users SET daily_goal = ? WHERE id = ?"), (int(goal), user_id))

    # --- attempts
    def add_math(self, user_id, category, level, question, answer, given, correct, seconds):
        with self._conn() as (con, cur):
            cur.execute(self._q("INSERT INTO math_attempts (user_id, ts, category, level, question, answer, given, "
                                "correct, seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"),
                        (user_id, _now(), category, level, question, answer, given, int(bool(correct)), float(seconds)))

    def add_memory(self, user_id, length, direction, style, correct, digits_right):
        with self._conn() as (con, cur):
            cur.execute(self._q("INSERT INTO memory_attempts (user_id, ts, length, direction, style, correct, "
                                "digits_right) VALUES (?, ?, ?, ?, ?, ?, ?)"),
                        (user_id, _now(), int(length), direction, style, int(bool(correct)), int(digits_right)))

    def _df(self, table, user_id):
        with self._conn() as (con, cur):
            cur.execute(self._q(f"SELECT * FROM {table} WHERE user_id = ? ORDER BY ts"), (user_id,))
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=cols)
        if len(df):
            df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
            df["correct"] = df["correct"].astype(bool)
        return df

    def math_df(self, user_id):
        return self._df("math_attempts", user_id)

    def memory_df(self, user_id):
        return self._df("memory_attempts", user_id)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
