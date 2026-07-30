"""utils/feedback_store.py — Thumbs up/down feedback stored in SQLite.
Accumulates question, chunks, answer, rating → future fine-tuning dataset."""
import sqlite3
import json
import os
import time
from typing import Optional, List, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cache", "feedback.db"
)


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   REAL,
            question    TEXT,
            answer      TEXT,
            chunks_json TEXT,
            rating      INTEGER,   -- 1 = thumbs up, -1 = thumbs down
            comment     TEXT,
            provider    TEXT,
            doc_sources TEXT
        )
    """)
    conn.commit()
    return conn


def store_feedback(question: str, answer: str,
                   chunks: List[Dict[str, Any]],
                   rating: int,
                   comment: str = "",
                   provider: str = "",
                   doc_sources: Optional[List[str]] = None) -> int:
    """
    Store one feedback record. rating: 1=good, -1=bad.
    Returns the new row id.
    """
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO feedback
           (timestamp, question, answer, chunks_json, rating, comment, provider, doc_sources)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            time.time(),
            question,
            answer,
            json.dumps([{"text": c.get("text", ""), "source": c.get("source", ""),
                         "page_number": c.get("page_number")} for c in (chunks or [])]),
            rating,
            comment,
            provider,
            json.dumps(doc_sources or []),
        )
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    logger.info(f"Feedback stored id={row_id} rating={rating}")
    return row_id


def get_feedback_stats() -> Dict[str, Any]:
    """Return aggregate stats for the feedback database."""
    try:
        conn = _get_conn()
        cur = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END),"
            "SUM(CASE WHEN rating=-1 THEN 1 ELSE 0 END) FROM feedback"
        )
        total, up, down = cur.fetchone()
        conn.close()
        return {
            "total": total or 0,
            "thumbs_up": up or 0,
            "thumbs_down": down or 0,
            "satisfaction_pct": round((up or 0) / max(total or 1, 1) * 100, 1),
        }
    except Exception as e:
        logger.error(f"Feedback stats error: {e}")
        return {"total": 0, "thumbs_up": 0, "thumbs_down": 0, "satisfaction_pct": 0}


def export_as_training_data(output_path: Optional[str] = None) -> str:
    """
    Export all positive-rated feedback as JSONL fine-tuning data.
    Format: {"prompt": question, "completion": answer, "context": chunks}
    """
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(DB_PATH), "training_data.jsonl"
        )

    conn = _get_conn()
    rows = conn.execute(
        "SELECT question, answer, chunks_json, rating FROM feedback ORDER BY timestamp"
    ).fetchall()
    conn.close()

    lines = []
    for question, answer, chunks_json, rating in rows:
        try:
            chunks = json.loads(chunks_json or "[]")
        except Exception:
            chunks = []
        lines.append(json.dumps({
            "prompt": question,
            "completion": answer,
            "context": [c.get("text", "") for c in chunks[:3]],
            "rating": rating,
        }))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def get_recent_feedback(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch recent feedback records for the eval dashboard."""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, timestamp, question, answer, rating, comment, provider "
            "FROM feedback ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "timestamp": r[1], "question": r[2],
             "answer": r[3][:200], "rating": r[4], "comment": r[5], "provider": r[6]}
            for r in rows
        ]
    except Exception as e:
        logger.error(f"get_recent_feedback error: {e}")
        return []


def render_feedback_buttons(question: str, answer: str,
                             chunks: List[Dict[str, Any]],
                             provider: str = "",
                             key_prefix: str = "fb") -> None:
    """Render thumbs up/down feedback buttons in Streamlit."""
    import streamlit as st

    col1, col2, col3 = st.columns([1, 1, 6])
    with col1:
        if st.button("👍", key=f"{key_prefix}_up",
                     help="This answer was helpful"):
            store_feedback(question, answer, chunks, rating=1, provider=provider)
            st.toast("Thanks for the feedback! 🙏")
    with col2:
        if st.button("👎", key=f"{key_prefix}_down",
                     help="This answer needs improvement"):
            store_feedback(question, answer, chunks, rating=-1, provider=provider)
            st.toast("Feedback noted — we'll improve!")
