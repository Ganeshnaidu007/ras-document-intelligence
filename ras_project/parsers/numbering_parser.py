"""parsers/numbering_parser.py — Detect and normalise question/list numbering styles."""
import re
from typing import Optional, Tuple


_STYLES = [
    ("decimal",  re.compile(r"^(\d+)[.)\]]")),
    ("alpha",    re.compile(r"^([a-zA-Z])[.)\]]")),
    ("roman",    re.compile(r"^([ivxIVX]+)[.)\]]")),
    ("q_prefix", re.compile(r"^(Q\s*\d+)[.:\)]", re.IGNORECASE)),
    ("bullet",   re.compile(r"^[•\-\*]\s")),
]


def detect_style(line: str) -> Optional[str]:
    for name, pat in _STYLES:
        if pat.match(line.strip()):
            return name
    return None


def extract_number(line: str) -> Tuple[Optional[str], str]:
    """Return (number_prefix, remaining_text)."""
    for _, pat in _STYLES:
        m = pat.match(line.strip())
        if m:
            prefix = m.group(0).rstrip()
            rest   = line.strip()[len(prefix):].strip()
            return prefix, rest
    return None, line.strip()


def normalise(prefix: str) -> int:
    """Convert any prefix to an integer index (best-effort)."""
    digits = re.sub(r"\D","",prefix)
    if digits: return int(digits)
    alpha = re.sub(r"[^a-zA-Z]","",prefix).lower()
    if alpha: return ord(alpha[0]) - ord("a") + 1
    return 0
