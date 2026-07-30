"""utils/file_utils.py — File system utilities."""
import os, hashlib
from typing import Optional


def file_hash(path: str) -> str:
    """Return MD5 hash of a file for deduplication / cache keying."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def file_size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 * 1024)


def list_files(directory: str, ext: Optional[str] = None):
    if not os.path.isdir(directory):
        return []
    files = [os.path.join(directory, f) for f in os.listdir(directory)]
    if ext:
        ext = ext.lstrip(".")
        files = [f for f in files if f.rsplit(".",1)[-1].lower() == ext]
    return files
