"""utils/timing.py — Lightweight stage timer.

Wrap any block in `with timed("stage name"):` and it logs how long that
stage took, at INFO level, so slow steps are visible in the terminal
without needing an external profiler.

Also keeps a running session summary you can print at the end of a run
with `print_summary()`.
"""
import time
from collections import defaultdict
from contextlib import contextmanager
from utils.logger import get_logger

logger = get_logger("timing")
_SESSION_TOTALS = defaultdict(float)
_SESSION_COUNTS = defaultdict(int)


@contextmanager
def timed(label: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _SESSION_TOTALS[label] += elapsed
        _SESSION_COUNTS[label] += 1
        logger.info(f"[TIMING] {label}: {elapsed:.2f}s")


def print_summary():
    if not _SESSION_TOTALS:
        return
    logger.info("[TIMING] ── Session summary (slowest first) ──")
    for label, total in sorted(_SESSION_TOTALS.items(), key=lambda x: -x[1]):
        n = _SESSION_COUNTS[label]
        avg = total / n
        logger.info(f"[TIMING]   {label:<30s} total={total:6.2f}s  calls={n:3d}  avg={avg:.2f}s")


def reset_summary():
    _SESSION_TOTALS.clear()
    _SESSION_COUNTS.clear()
