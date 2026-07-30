"""utils/helpers.py — Miscellaneous helper functions."""
import os, uuid, shutil
from typing import List
from config.settings import TEMP_DIR
from utils.logger import get_logger
logger = get_logger(__name__)


def user_temp_dir(user_id) -> str:
    """temp/users/{user_id}/ — every user gets their own scratch space, so
    concurrent uploads/cleanups never touch each other's files."""
    d = os.path.join(TEMP_DIR, "users", str(user_id))
    os.makedirs(d, exist_ok=True)
    return d


def save_uploaded_file(uploaded_file, subfolder: str = "", user_id=None) -> str:
    """Save a Streamlit UploadedFile to a temp directory and return the path.

    Pass user_id (always, in this app) to scope the file under
    temp/users/{user_id}/{subfolder}/ instead of the old shared temp/{subfolder}/.
    Without it, two users uploading at the same moment share one directory,
    and one user's cleanup_temp_files() call deletes the other's in-flight
    upload out from under them mid-pipeline.
    """
    base = user_temp_dir(user_id) if user_id is not None else TEMP_DIR
    dest_dir = os.path.join(base, subfolder)
    os.makedirs(dest_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
    dest_path = os.path.join(dest_dir, safe_name)
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    logger.debug(f"Saved {uploaded_file.name} → {dest_path}")
    return dest_path


def cleanup_temp_files(user_id=None):
    """Remove temp files. Pass user_id to only clear THAT user's scratch
    directory — never call this with no user_id in a multi-user app, or
    you'll delete every other concurrently-active user's uploads too."""
    target_dir = user_temp_dir(user_id) if user_id is not None else TEMP_DIR
    try:
        for item in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        logger.debug(f"Temp files cleaned up ({target_dir}).")
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower().lstrip(".")


def chunk_list(lst: list, size: int) -> List[list]:
    return [lst[i:i+size] for i in range(0, len(lst), size)]


def source_confidence(c: dict):
    """Normalise whatever relevance score a chunk carries (cross-encoder
    rerank logit, Cohere 0-1 relevance, or hybrid/cosine score) into a
    0-100 'source confidence' percentage plus a High/Medium/Low label,
    so citations can show how strongly each source backs the answer —
    not just the overall answer confidence.

    Returns None if the chunk has no score at all (e.g. a raw web result
    that skipped reranking).
    """
    import math

    if "rerank_score" in c and c["rerank_score"] is not None:
        sc = c["rerank_score"]
        # Cohere's rerank already returns a 0-1 relevance probability.
        # The local cross-encoder (ms-marco-MiniLM) returns an unbounded
        # logit, roughly -10..10 — squash that with a sigmoid so it reads
        # as a percentage. Values already in [0,1] pass through untouched.
        pct = sc * 100 if 0.0 <= sc <= 1.0 else (1 / (1 + math.exp(-sc))) * 100
    else:
        sc = c.get("hybrid_score", c.get("cosine_score"))
        if sc is None:
            return None
        pct = max(0.0, min(1.0, sc)) * 100

    pct = round(pct)
    if pct >= 70:   label = "High"
    elif pct >= 40: label = "Medium"
    else:           label = "Low"
    return {"pct": pct, "label": label}


def sort_by_confidence(chunks: list) -> list:
    """Sort source chunks highest-match first, so 'Source highlights' /
    'Source passages' always reads strongest evidence to weakest instead
    of whatever order retrieval happened to return them in."""
    def _pct(c):
        conf = source_confidence(c)
        return conf["pct"] if conf else -1
    return sorted(chunks or [], key=_pct, reverse=True)
