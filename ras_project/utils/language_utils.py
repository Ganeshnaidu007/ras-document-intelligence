"""utils/language_utils.py — Language detection and Unicode utilities."""
import re, unicodedata


DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
TELUGU_RE     = re.compile(r"[\u0C00-\u0C7F]")


def detect_language(text: str) -> str:
    has_hi = bool(DEVANAGARI_RE.search(text))
    has_te = bool(TELUGU_RE.search(text))
    if has_hi and has_te: return "Mixed Language"
    if has_hi:            return "Hindi"
    if has_te:            return "Telugu"
    return "English"


def is_rtl(text: str) -> bool:
    for ch in text:
        if unicodedata.bidirectional(ch) in ("R", "AL"):
            return True
    return False


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def safe_encode(text: str) -> bytes:
    return text.encode("utf-8", errors="replace")


def contains_hindi(text: str) -> bool:
    return bool(DEVANAGARI_RE.search(text))


def contains_telugu(text: str) -> bool:
    return bool(TELUGU_RE.search(text))
