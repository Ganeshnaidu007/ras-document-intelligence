"""utils/async_processor.py — Tracks indexing job status for the UI progress bar.

IMPORTANT DESIGN NOTE
---------------------
The original "start indexing the moment a file is uploaded" design caused a
race condition: the background thread and the main pipeline thread both tried
to parse the same PDF at the same time, deadlocking on Windows (PyMuPDF /
torch are not multi-thread-safe when loading the same file path concurrently).

The new design is simpler and correct:
  - Background indexing is ONLY started by run_pipeline() (main thread).
  - This module is now a thin job-status tracker used by the progress bar.
  - _trigger_async_indexing() in app.py is a no-op stub kept for compatibility.
"""
import threading
import time
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def _job_id(file_names) -> str:
    import hashlib
    key = "|".join(sorted(file_names))
    return hashlib.md5(key.encode()).hexdigest()[:12]


def register_job(jid: str) -> None:
    """Register a new job as running (called from main pipeline thread)."""
    with _lock:
        _jobs[jid] = {
            "status": "running",
            "progress": 0,
            "message": "Starting…",
            "result": None,
            "error": None,
            "started_at": time.time(),
        }


def update_job(jid: str, progress: int, message: str) -> None:
    with _lock:
        if jid in _jobs:
            _jobs[jid]["progress"] = progress
            _jobs[jid]["message"] = message


def complete_job(jid: str, result: Dict[str, Any]) -> None:
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "done"
            _jobs[jid]["result"] = result


def fail_job(jid: str, error: str) -> None:
    with _lock:
        if jid in _jobs:
            _jobs[jid]["status"] = "error"
            _jobs[jid]["error"] = error


def get_job_status(jid: str) -> Dict[str, Any]:
    with _lock:
        return dict(_jobs.get(jid, {"status": "not_found", "progress": 0, "message": ""}))


def get_job_result(jid: str) -> Optional[Dict[str, Any]]:
    with _lock:
        job = _jobs.get(jid, {})
        if job.get("status") == "done":
            return job.get("result")
    return None


def cancel_all_jobs() -> None:
    with _lock:
        _jobs.clear()


# ── Legacy stub — kept so app.py import doesn't break ─────────────────────────
def start_background_indexing(source_files, settings, on_complete=None) -> str:
    """
    NO-OP stub. Background pre-indexing is disabled because it races with
    the main pipeline when the user clicks Generate before it finishes.
    The main pipeline (run_pipeline in app.py) does all indexing synchronously
    on the main thread, which is safe and fast thanks to the embedding cache.
    """
    file_names = [f.name for f in source_files]
    jid = _job_id(file_names)
    logger.info(f"start_background_indexing: pre-indexing disabled, jid={jid} ignored")
    return jid