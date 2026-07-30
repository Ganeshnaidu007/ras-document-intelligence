"""embeddings/embedding_cache.py — Disk cache for embeddings keyed by file hash.

Saves chunk embeddings as .npy files so re-uploading the same PDF
skips embedding entirely — 10x faster on repeat runs.
"""
import os, json, hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from utils.logger import get_logger
from config.settings import CACHE_DIR
logger = get_logger(__name__)

EMBED_CACHE_DIR = os.path.join(CACHE_DIR, "embeddings")
os.makedirs(EMBED_CACHE_DIR, exist_ok=True)


def _file_hash(path: str) -> str:
    """SHA-256 of file contents — same file = same hash regardless of filename."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()[:16]


def _cache_key(file_path: str, model_name: str, chunk_size: int, chunk_overlap: int, method: str) -> str:
    """Unique cache key = file content + embedding model + chunking params."""
    fhash = _file_hash(file_path)
    params = f"{model_name}|{chunk_size}|{chunk_overlap}|{method}"
    phash  = hashlib.md5(params.encode()).hexdigest()[:8]
    return f"{fhash}_{phash}"


def load_cached(cache_key: str) -> Optional[Tuple[List[Dict[str, Any]], List[List[float]]]]:
    """Return (chunks, embeddings) if cache hit, else None."""
    meta_path  = os.path.join(EMBED_CACHE_DIR, f"{cache_key}_meta.json")
    embed_path = os.path.join(EMBED_CACHE_DIR, f"{cache_key}_vecs.npy")
    if not os.path.exists(meta_path) or not os.path.exists(embed_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        vecs = np.load(embed_path).tolist()
        for c, v in zip(chunks, vecs):
            c["embedding"] = v
        logger.info(f"Embedding cache HIT: {cache_key} ({len(chunks)} chunks)")
        return chunks, vecs
    except Exception as e:
        logger.warning(f"Cache load failed ({cache_key}): {e}")
        return None


def save_cache(cache_key: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
    """Persist chunks + embeddings to disk."""
    meta_path  = os.path.join(EMBED_CACHE_DIR, f"{cache_key}_meta.json")
    embed_path = os.path.join(EMBED_CACHE_DIR, f"{cache_key}_vecs.npy")
    try:
        # Save chunks without embeddings (stored separately in npy)
        slim = [{k: v for k, v in c.items() if k != "embedding"} for c in chunks]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(slim, f, ensure_ascii=False)
        np.save(embed_path, np.array(embeddings, dtype="float32"))
        size_mb = os.path.getsize(embed_path) / 1024 / 1024
        logger.info(f"Embedding cache SAVED: {cache_key} ({len(chunks)} chunks, {size_mb:.1f} MB)")
    except Exception as e:
        logger.warning(f"Cache save failed ({cache_key}): {e}")


def get_cache_stats() -> Dict[str, Any]:
    """Return stats about the current cache for display in UI."""
    files = [f for f in os.listdir(EMBED_CACHE_DIR) if f.endswith("_vecs.npy")]
    total_mb = sum(
        os.path.getsize(os.path.join(EMBED_CACHE_DIR, f)) for f in files
    ) / 1024 / 1024
    return {"entries": len(files), "total_mb": round(total_mb, 1)}


def clear_cache():
    """Delete all cached embeddings."""
    count = 0
    for f in os.listdir(EMBED_CACHE_DIR):
        try:
            os.remove(os.path.join(EMBED_CACHE_DIR, f)); count += 1
        except Exception:
            pass
    logger.info(f"Cleared {count} cache files")
    return count