"""db/user_store.py — All reads/writes for per-user data.

Handles: real accounts (username + password, PBKDF2-hashed), individual
document storage (one chunk+embedding file per document, so any subset can
be reused in any chat), chat sessions, Q&A history, and a daily upload cap.
"""
import os, json, time, hashlib, secrets, hmac
import numpy as np
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from config.settings import USER_DOCS_DIR, MAX_UPLOADS_PER_DAY, MIN_PASSWORD_LENGTH
from db.schema import get_conn, init_db

logger = get_logger(__name__)
init_db()  # safe to call repeatedly — CREATE TABLE IF NOT EXISTS + migrations

# Login lockout: after this many wrong passwords in a row, the account is
# locked for LOCKOUT_SECONDS. Resets to 0 on any successful login. This is
# what stops unlimited password-guessing against a single account.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS      = 15 * 60

# Admin alerting: flag a user in the admin dashboard if they've hit their
# daily upload cap this many times within this many hours — a signal they
# either need a higher personal cap or are testing the limits.
CAP_ALERT_THRESHOLD    = 2
CAP_ALERT_WINDOW_HOURS = 24


def normalize_username(name: str) -> str:
    return " ".join(name.strip().lower().split())


# ── Password hashing (PBKDF2-SHA256, per-user random salt) ─────────────────
# Standard-library only (hashlib), no plaintext password ever stored or
# logged. 200k iterations is a reasonable modern default for PBKDF2.
_ITERATIONS = 200_000


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS).hex()


class AuthError(Exception):
    """Bad username/password combo, or username already taken at signup."""


class UploadLimitExceeded(Exception):
    """This user has hit their daily new-upload cap."""


SECURITY_QUESTIONS = [
    "What was the name of your first school?",
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "What is your favorite book?",
]


def _hash_answer(answer: str, salt: str) -> str:
    # Case/whitespace-insensitive so "Blue" and "blue " both work later.
    normalized = answer.strip().lower()
    return hashlib.pbkdf2_hmac("sha256", normalized.encode(), salt.encode(), _ITERATIONS).hex()


def register_user(username: str, password: str, security_question: str,
                  security_answer: str) -> Dict[str, Any]:
    key = normalize_username(username)
    if not key:
        raise AuthError("Username can't be empty.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not security_question.strip():
        raise AuthError("Choose a security question.")
    if not security_answer.strip():
        raise AuthError("Answer your security question — you'll need it to recover your account.")

    conn = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE username=?", (key,)).fetchone()
    if existing:
        conn.close()
        raise AuthError("That username is already taken.")

    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    ans_salt = secrets.token_hex(16)
    ans_hash = _hash_answer(security_answer, ans_salt)
    now = time.time()
    cur = conn.execute(
        "INSERT INTO users (username, display_name, password_hash, password_salt, "
        "created_at, last_active, security_question, security_answer_hash, security_answer_salt) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (key, username.strip(), pw_hash, salt, now, now,
         security_question.strip(), ans_hash, ans_salt))
    user_id = cur.lastrowid
    conn.execute("INSERT INTO sessions (user_id, login_time, last_seen) VALUES (?,?,?)",
                 (user_id, now, now))
    conn.commit(); conn.close()
    logger.info(f"New account: {username} (id={user_id})")
    return {"id": user_id, "username": key, "display_name": username.strip()}


def get_security_question(username: str) -> Optional[str]:
    """Returns the account's security question, or None if the username
    doesn't exist. Callers should show a generic 'check your username'
    message either way rather than saying 'not found' — see auth/auth.py."""
    conn = get_conn()
    row = conn.execute("SELECT security_question FROM users WHERE username=?",
                       (normalize_username(username),)).fetchone()
    conn.close()
    return row[0] if row else None


def reset_password_with_security_answer(username: str, answer: str, new_password: str):
    """Forgot-password flow: verify the security answer, then set a new
    password directly (no admin involved, no email needed)."""
    key = normalize_username(username)
    conn = get_conn()
    row = conn.execute(
        "SELECT id, security_answer_hash, security_answer_salt FROM users WHERE username=?",
        (key,)).fetchone()
    conn.close()
    if not row or not row[1]:
        raise AuthError("Incorrect answer.")
    user_id, ans_hash, ans_salt = row
    if not hmac.compare_digest(_hash_answer(answer, ans_salt), ans_hash):
        raise AuthError("Incorrect answer.")
    reset_password(user_id, new_password, force_change=False)
    logger.info(f"Password reset via security question for user_id={user_id}")


def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    key = normalize_username(username)
    conn = get_conn()
    row = conn.execute(
        "SELECT id, display_name, password_hash, password_salt, failed_attempts, "
        "locked_until, must_change_password FROM users WHERE username=?",
        (key,)).fetchone()
    if not row:
        conn.close()
        # Deliberately the same message as "wrong password" — don't reveal
        # whether a username exists at all.
        raise AuthError("Incorrect username or password.")

    user_id, display_name, pw_hash, salt, failed_attempts, locked_until, must_change = row

    if locked_until and time.time() < locked_until:
        wait_min = max(1, int((locked_until - time.time()) / 60) + 1)
        conn.close()
        raise AuthError(f"Too many failed attempts. Try again in about {wait_min} minute(s).")

    # Constant-time comparison — a plain `!=` leaks timing information about
    # how many leading bytes of the hash matched, which is a real (if slow)
    # attack against password hashes over enough attempts.
    ok = hmac.compare_digest(_hash_password(password, salt), pw_hash)

    if not ok:
        new_failed = failed_attempts + 1
        lock_until = time.time() + LOCKOUT_SECONDS if new_failed >= MAX_FAILED_ATTEMPTS else None
        conn.execute("UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
                    (new_failed, lock_until, user_id))
        conn.commit(); conn.close()
        if lock_until:
            raise AuthError(f"Too many failed attempts. Account locked for "
                            f"{LOCKOUT_SECONDS // 60} minutes.")
        raise AuthError("Incorrect username or password.")

    now = time.time()
    conn.execute("UPDATE users SET last_active=?, failed_attempts=0, locked_until=NULL WHERE id=?",
                (now, user_id))
    conn.execute("INSERT INTO sessions (user_id, login_time, last_seen) VALUES (?,?,?)",
                (user_id, now, now))
    conn.commit(); conn.close()
    return {"id": user_id, "username": key, "display_name": display_name,
            "must_change_password": bool(must_change)}


def _random_password(length: int = 12) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def reset_password(user_id: int, new_password: str, force_change: bool = False):
    """Set a new password directly. Used by both self-service change and
    admin-triggered reset (see admin_reset_password below)."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(new_password, salt)
    conn = get_conn()
    conn.execute(
        "UPDATE users SET password_hash=?, password_salt=?, failed_attempts=0, "
        "locked_until=NULL, must_change_password=? WHERE id=?",
        (pw_hash, salt, 1 if force_change else 0, user_id))
    conn.commit(); conn.close()
    logger.info(f"Password reset for user_id={user_id} (forced_change={force_change})")


def admin_reset_password(user_id: int) -> str:
    """Admin-triggered reset: generates a random temporary password, forces
    the user to change it on next login, and returns the temp password once
    (for the admin to relay to the user out-of-band — it is never stored or
    logged in plaintext anywhere)."""
    temp_password = _random_password()
    reset_password(user_id, temp_password, force_change=True)
    log_admin_action("reset_password", target=f"user_id={user_id}")
    return temp_password


def change_own_password(user_id: int, old_password: str, new_password: str):
    """Self-service change — requires knowing the current password."""
    conn = get_conn()
    row = conn.execute("SELECT password_hash, password_salt FROM users WHERE id=?",
                       (user_id,)).fetchone()
    conn.close()
    if not row:
        raise AuthError("Account not found.")
    pw_hash, salt = row
    if not hmac.compare_digest(_hash_password(old_password, salt), pw_hash):
        raise AuthError("Current password is incorrect.")
    reset_password(user_id, new_password, force_change=False)


def touch_user(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET last_active=? WHERE id=?", (time.time(), user_id))
    conn.commit(); conn.close()


# ── Daily upload cap ─────────────────────────────────────────────────────────
def documents_uploaded_today(user_id: int) -> int:
    cutoff = time.time() - 86400  # rolling 24h, not calendar day
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM documents WHERE user_id=? AND created_at >= ?",
        (user_id, cutoff)).fetchone()[0]
    conn.close()
    return n


def uploads_remaining_today(user_id: int) -> int:
    return max(0, MAX_UPLOADS_PER_DAY - documents_uploaded_today(user_id))


# ── Individual document storage (one file per document) ────────────────────
def _doc_paths(user_id: int, doc_id: int):
    base = os.path.join(USER_DOCS_DIR, str(user_id))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"doc_{doc_id}_meta.json"), os.path.join(base, f"doc_{doc_id}_vecs.npy")


def save_document(user_id: int, filename: str, chunks: List[Dict[str, Any]], file_hash: str,
                  chunking_method: str, chunk_size: int, chunk_overlap: int,
                  embedding_model: str, source_file_path: Optional[str] = None) -> int:
    """Save ONE document's chunks+embeddings as its own file and register it
    in the library. Returns the new documents.id. Enforces the daily upload
    cap as a hard backstop (callers should also check uploads_remaining_today
    BEFORE doing the expensive parse/chunk/embed work, to avoid wasting it).

    If source_file_path is given, a permanent copy is kept alongside the
    chunks (data/user_documents/{user_id}/doc_{id}_source{ext}) — this is
    what lets "View in PDF" reopen the original file later to render a
    highlighted page. Without it, that feature just won't be offered for
    this document (e.g. non-PDF sources, or callers that don't have the
    original file handy)."""
    if documents_uploaded_today(user_id) >= MAX_UPLOADS_PER_DAY:
        log_cap_hit(user_id)
        raise UploadLimitExceeded(
            f"Daily upload limit reached ({MAX_UPLOADS_PER_DAY} files per 24h). Try again later.")

    conn = get_conn()
    cur = conn.execute("""INSERT INTO documents
        (user_id, filename, file_hash, num_chunks, chunking_method, chunk_size, chunk_overlap,
         embedding_model, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, filename, file_hash, len(chunks), chunking_method, chunk_size, chunk_overlap,
         embedding_model, time.time()))
    doc_id = cur.lastrowid

    meta_path, vecs_path = _doc_paths(user_id, doc_id)
    slim = [{k: v for k, v in c.items() if k != "embedding"} for c in chunks]
    vecs = [c.get("embedding") or [] for c in chunks]
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False)
    np.save(vecs_path, np.array(vecs, dtype="float32"))

    source_path = None
    if source_file_path and os.path.exists(source_file_path) and source_file_path.lower().endswith(".pdf"):
        base = os.path.join(USER_DOCS_DIR, str(user_id))
        os.makedirs(base, exist_ok=True)
        source_path = os.path.join(base, f"doc_{doc_id}_source.pdf")
        try:
            import shutil
            shutil.copyfile(source_file_path, source_path)
        except OSError as e:
            logger.warning(f"Could not persist source PDF for doc {doc_id}: {e}")
            source_path = None

    conn.execute("UPDATE documents SET chunks_path=?, source_path=? WHERE id=?",
                (meta_path, source_path, doc_id))
    conn.commit(); conn.close()
    logger.info(f"Saved document {doc_id} ({filename}) for user {user_id}: {len(chunks)} chunks")
    return doc_id


def get_document_source_path(doc_id: int, user_id: int) -> Optional[str]:
    """The permanent copy of the original PDF for this document, if one was
    kept (see save_document). Used by the 'View in PDF' source feature."""
    conn = get_conn()
    row = conn.execute("SELECT source_path FROM documents WHERE id=? AND user_id=?",
                       (doc_id, user_id)).fetchone()
    conn.close()
    return row[0] if row and row[0] and os.path.exists(row[0]) else None


def list_user_documents(user_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, filename, num_chunks, embedding_model, created_at FROM documents "
        "WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [{"id": r[0], "filename": r[1], "num_chunks": r[2], "embedding_model": r[3],
             "created_at": r[4]} for r in rows]


def load_documents_chunks(doc_ids: List[int]) -> List[Dict[str, Any]]:
    """Load and concatenate chunks+embeddings for a set of document IDs."""
    if not doc_ids:
        return []
    conn = get_conn()
    placeholders = ",".join("?" * len(doc_ids))
    rows = conn.execute(
        f"SELECT id, user_id, chunks_path FROM documents WHERE id IN ({placeholders})",
        doc_ids).fetchall()
    conn.close()
    all_chunks = []
    for doc_id, user_id, meta_path in rows:
        if not meta_path:
            continue
        vecs_path = meta_path.replace("_meta.json", "_vecs.npy")
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
            vecs = np.load(vecs_path).tolist()
            for c, v in zip(chunks, vecs):
                c["embedding"] = v
                # BUG FIX: c["source"] is the filename at the moment this
                # document was first uploaded/chunked and never changes —
                # but a document can be renamed later (documents.filename
                # in the DB). The "View" button used to join on that stale
                # name, so any renamed doc could never be found and always
                # showed "Original PDF isn't available". Attaching the real
                # doc_id here lets the UI look the source path up directly,
                # with no name matching involved at all.
                c["_doc_id"] = doc_id
            all_chunks.extend(chunks)
        except Exception as e:
            logger.warning(f"Could not load document {doc_id}: {e}")
    return all_chunks


def rename_document(doc_id: int, user_id: int, new_filename: str) -> bool:
    """Rename a document's display name. Scoped to user_id so one user can
    never rename (or probe the existence of) another user's document by ID."""
    new_filename = new_filename.strip()[:200]
    if not new_filename:
        return False
    conn = get_conn()
    cur = conn.execute("UPDATE documents SET filename=? WHERE id=? AND user_id=?",
                       (new_filename, doc_id, user_id))
    conn.commit(); conn.close()
    return cur.rowcount > 0


def delete_document(doc_id: int, user_id: int) -> bool:
    """Scoped to user_id: this used to accept a bare doc_id with no
    ownership check, meaning any logged-in user who guessed/enumerated a
    document ID could delete someone else's file. Every caller now passes
    the current user's id and this verifies the row actually belongs to
    them before touching anything."""
    conn = get_conn()
    row = conn.execute("SELECT chunks_path, source_path FROM documents WHERE id=? AND user_id=?",
                       (doc_id, user_id)).fetchone()
    if not row:
        conn.close()
        return False
    if row[0]:
        for p in (row[0], row[0].replace("_meta.json", "_vecs.npy")):
            try:
                if os.path.exists(p): os.remove(p)
            except OSError: pass
    if row[1]:
        try:
            if os.path.exists(row[1]): os.remove(row[1])
        except OSError: pass
    conn.execute("DELETE FROM documents WHERE id=? AND user_id=?", (doc_id, user_id))
    conn.commit(); conn.close()
    return True


# ── Chat sessions ────────────────────────────────────────────────────────────
def create_chat_session(user_id: int, title: str = "New chat") -> int:
    now = time.time()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO chat_sessions (user_id, title, doc_ids, created_at, updated_at) "
        "VALUES (?,?,?,?,?)", (user_id, title, "[]", now, now))
    sid = cur.lastrowid
    conn.commit(); conn.close()
    return sid


def list_chat_sessions(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, title, doc_ids, created_at, updated_at FROM chat_sessions "
        "WHERE user_id=? ORDER BY updated_at DESC LIMIT ?", (user_id, limit)).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "doc_ids": json.loads(r[2] or "[]"),
             "created_at": r[3], "updated_at": r[4]} for r in rows]


def get_chat_session(session_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute(
        "SELECT id, user_id, title, doc_ids, created_at, updated_at FROM chat_sessions WHERE id=?",
        (session_id,)).fetchone()
    conn.close()
    if not row: return None
    return {"id": row[0], "user_id": row[1], "title": row[2],
            "doc_ids": json.loads(row[3] or "[]"), "created_at": row[4], "updated_at": row[5]}


def update_session_docs(session_id: int, doc_ids: List[int]):
    conn = get_conn()
    conn.execute("UPDATE chat_sessions SET doc_ids=?, updated_at=? WHERE id=?",
                (json.dumps(doc_ids), time.time(), session_id))
    conn.commit(); conn.close()


def rename_session(session_id: int, title: str):
    conn = get_conn()
    conn.execute("UPDATE chat_sessions SET title=? WHERE id=?", (title[:60], session_id))
    conn.commit(); conn.close()


def touch_session(session_id: int):
    conn = get_conn()
    conn.execute("UPDATE chat_sessions SET updated_at=? WHERE id=?", (time.time(), session_id))
    conn.commit(); conn.close()


def delete_session(session_id: int):
    """Delete a chat session and its Q&A history. Documents in the user's
    library are untouched — deleting a chat never deletes uploaded files."""
    conn = get_conn()
    conn.execute("DELETE FROM qa_history WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM chat_sessions WHERE id=?", (session_id,))
    conn.commit(); conn.close()


# ── Q&A history (per chat session) ──────────────────────────────────────────
def save_qa_turn(user_id: int, session_id: Optional[int], question: str, answer: str,
                 doc_sources: str = "", provider: str = "", mode: str = "chat"):
    conn = get_conn()
    conn.execute("""INSERT INTO qa_history
        (user_id, session_id, question, answer, doc_sources, provider, mode, timestamp)
        VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, session_id, question, answer, doc_sources, provider, mode, time.time()))
    conn.commit(); conn.close()
    if session_id:
        touch_session(session_id)


def get_session_history(session_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT question, answer, timestamp FROM qa_history "
        "WHERE session_id=? ORDER BY timestamp ASC", (session_id,)).fetchall()
    conn.close()
    return [{"question": r[0], "answer": r[1], "timestamp": r[2]} for r in rows]


def session_is_empty(session_id: int) -> bool:
    """True if this chat session has never had a message sent in it. Used
    to avoid piling up duplicate blank 'New chat' rows — reuse an empty
    session instead of creating another one."""
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM qa_history WHERE session_id=? LIMIT 1",
                       (session_id,)).fetchone()
    conn.close()
    return row is None


def prune_empty_sessions(user_id: int, keep_session_id: int = None):
    """Delete blank, never-used 'New chat' sessions for this user, except
    keep_session_id. Self-heals accounts that already accumulated duplicate
    empty chats (e.g. from repeatedly clicking 'New chat' before this fix),
    and keeps that from happening going forward. Never touches a session
    that has any Q&A history or a custom (renamed) title."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id FROM chat_sessions WHERE user_id=? AND title='New chat'",
        (user_id,)).fetchall()
    conn.close()
    for (sid,) in rows:
        if sid == keep_session_id:
            continue
        if session_is_empty(sid):
            delete_session(sid)


# ── Deletion (admin action) ──────────────────────────────────────────────────
def delete_user_completely(user_id: int):
    conn = get_conn()
    doc_paths = conn.execute("SELECT chunks_path FROM documents WHERE user_id=?",
                             (user_id,)).fetchall()
    conn.close()
    for (p,) in doc_paths:
        if p:
            for f in (p, p.replace("_meta.json", "_vecs.npy")):
                try:
                    if os.path.exists(f): os.remove(f)
                except OSError: pass
    conn = get_conn()
    conn.execute("DELETE FROM qa_history WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM chat_sessions WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM documents WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM cap_hits WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit(); conn.close()


# ── Audit log (admin actions) ───────────────────────────────────────────────
def log_admin_action(action: str, target: str = "", actor: str = "admin"):
    conn = get_conn()
    conn.execute("INSERT INTO audit_log (actor, action, target, timestamp) VALUES (?,?,?,?)",
                (actor, action, target, time.time()))
    conn.commit(); conn.close()


def get_audit_log(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT actor, action, target, timestamp FROM audit_log "
        "ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [{"actor": r[0], "action": r[1], "target": r[2], "timestamp": r[3]} for r in rows]


# ── Upload-cap alerting ──────────────────────────────────────────────────────
def log_cap_hit(user_id: int):
    conn = get_conn()
    conn.execute("INSERT INTO cap_hits (user_id, timestamp) VALUES (?,?)", (user_id, time.time()))
    conn.commit(); conn.close()


def users_who_hit_cap_recently(hours: int = CAP_ALERT_WINDOW_HOURS,
                               min_hits: int = CAP_ALERT_THRESHOLD) -> List[Dict[str, Any]]:
    """Users who've hit their daily upload cap `min_hits`+ times in the last
    `hours` — surfaced in the admin dashboard as candidates for a higher cap."""
    cutoff = time.time() - hours * 3600
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.id, u.display_name, u.username, COUNT(*) AS hits
        FROM cap_hits c JOIN users u ON u.id = c.user_id
        WHERE c.timestamp >= ?
        GROUP BY c.user_id
        HAVING COUNT(*) >= ?
        ORDER BY hits DESC
    """, (cutoff, min_hits)).fetchall()
    conn.close()
    return [{"id": r[0], "display_name": r[1], "username": r[2], "hits": r[3]} for r in rows]


# ── Login history (shown back to the user, and to admin) ──────────────────────
def get_login_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT login_time FROM sessions WHERE user_id=? ORDER BY login_time DESC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    return [{"login_time": r[0]} for r in rows]


# ── Export a user's own Q&A history ────────────────────────────────────────────
def get_all_qa_for_user(user_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT question, answer, doc_sources, provider, mode, timestamp FROM qa_history "
        "WHERE user_id=? ORDER BY timestamp ASC", (user_id,)).fetchall()
    conn.close()
    return [{"question": r[0], "answer": r[1], "doc_sources": r[2],
             "provider": r[3], "mode": r[4], "timestamp": r[5]} for r in rows]


# ── Usage dashboard aggregates (admin) ─────────────────────────────────────────
def questions_per_day(days: int = 30) -> List[Dict[str, Any]]:
    since = time.time() - days * 86400
    conn = get_conn()
    rows = conn.execute(
        "SELECT date(timestamp, 'unixepoch') AS day, COUNT(*) AS n "
        "FROM qa_history WHERE timestamp >= ? GROUP BY day ORDER BY day", (since,)).fetchall()
    conn.close()
    return [{"day": r[0], "count": r[1]} for r in rows]


def top_documents(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT filename, COUNT(*) AS uploads, SUM(num_chunks) AS total_chunks "
        "FROM documents GROUP BY filename ORDER BY uploads DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [{"filename": r[0], "uploads": r[1], "total_chunks": r[2] or 0} for r in rows]


def most_active_users(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.display_name, u.username, COUNT(q.id) AS num_questions
        FROM qa_history q JOIN users u ON u.id = q.user_id
        GROUP BY q.user_id ORDER BY num_questions DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [{"display_name": r[0], "username": r[1], "num_questions": r[2]} for r in rows]


# ── Admin-facing aggregate stats ────────────────────────────────────────────
def list_all_users() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.id, u.display_name, u.username, u.created_at, u.last_active,
               (SELECT COUNT(*) FROM documents d WHERE d.user_id=u.id)     AS num_docs,
               (SELECT COUNT(*) FROM chat_sessions s WHERE s.user_id=u.id) AS num_sessions,
               (SELECT COUNT(*) FROM qa_history q WHERE q.user_id=u.id)    AS num_qa,
               (SELECT COALESCE(SUM(num_chunks),0) FROM documents d WHERE d.user_id=u.id) AS num_chunks
        FROM users u ORDER BY u.last_active DESC
    """).fetchall()
    conn.close()
    return [{"id": r[0], "display_name": r[1], "username": r[2], "created_at": r[3],
             "last_active": r[4], "num_docs": r[5], "num_sessions": r[6], "num_qa": r[7],
             "num_chunks": r[8]} for r in rows]


def disk_usage_mb() -> float:
    total = 0
    for root, _, files in os.walk(USER_DOCS_DIR):
        for f in files:
            try: total += os.path.getsize(os.path.join(root, f))
            except OSError: pass
    return round(total / 1024 / 1024, 2)
