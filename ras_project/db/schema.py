"""db/schema.py — SQLite schema for multi-user storage.

Seven tables:
  users          — one row per account (username + password hash), now also
                   tracking failed login attempts (lockout) and whether a
                   password reset is pending
  documents      — every file a person has uploaded, stored individually so
                   any subset can be picked into any chat later
  chat_sessions  — each "New chat" thread — its own title, its own history,
                   its own chosen subset of documents
  qa_history     — every question+answer, tied to a chat_session
  sessions       — lightweight login/activity log (also powers "recent
                   logins" shown back to the user)
  audit_log      — admin actions (e.g. deleting a user's data), so there's a
                   record of who did what and when
  cap_hits       — logged every time someone hits their daily upload limit,
                   so the admin dashboard can flag people who need a higher
                   cap instead of silently blocking them over and over

One SQLite file for the whole app (config.settings.USER_DB_PATH).
"""
import sqlite3
from utils.logger import get_logger
from config.settings import USER_DB_PATH

logger = get_logger(__name__)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(USER_DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _add_column_if_missing(conn, table, col, coltype):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
        logger.info(f"Migrated: added {table}.{col}")


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,     -- normalized (lowercase, trimmed)
            display_name  TEXT NOT NULL,             -- what they typed at signup
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at    REAL NOT NULL,
            last_active   REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename         TEXT NOT NULL,
            file_hash        TEXT,
            num_chunks       INTEGER DEFAULT 0,
            chunking_method  TEXT,
            chunk_size       INTEGER,
            chunk_overlap    INTEGER,
            embedding_model  TEXT,
            chunks_path      TEXT,             -- this doc's OWN chunk+embedding file
            created_at       REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
        CREATE INDEX IF NOT EXISTS idx_documents_user_created ON documents(user_id, created_at);

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       TEXT NOT NULL DEFAULT 'New chat',
            doc_ids     TEXT NOT NULL DEFAULT '[]',   -- JSON list of documents.id this chat uses
            created_at  REAL NOT NULL,
            updated_at  REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_id, updated_at);

        CREATE TABLE IF NOT EXISTS qa_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id  INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
            question    TEXT,
            answer      TEXT,
            doc_sources TEXT,
            provider    TEXT,
            mode        TEXT,             -- 'chat' or 'batch'
            timestamp   REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_qa_session ON qa_history(session_id, timestamp);

        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            login_time REAL NOT NULL,
            last_seen  REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            actor      TEXT NOT NULL,     -- 'admin' (only actor today; room to grow)
            action     TEXT NOT NULL,     -- e.g. 'delete_user'
            target     TEXT,              -- e.g. the affected username
            timestamp  REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cap_hits (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            timestamp  REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cap_hits_user ON cap_hits(user_id, timestamp);
    """)
    # Migrations for anyone upgrading from an earlier version of this schema
    _add_column_if_missing(conn, "documents", "chunks_path", "TEXT")
    _add_column_if_missing(conn, "qa_history", "session_id", "INTEGER")
    _add_column_if_missing(conn, "users", "failed_attempts", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "users", "locked_until", "REAL")
    _add_column_if_missing(conn, "users", "must_change_password", "INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "users", "security_question", "TEXT")
    _add_column_if_missing(conn, "users", "security_answer_hash", "TEXT")
    _add_column_if_missing(conn, "users", "security_answer_salt", "TEXT")
    _add_column_if_missing(conn, "documents", "source_path", "TEXT")
    conn.commit()
    conn.close()
    logger.info(f"User DB ready at {USER_DB_PATH}")
