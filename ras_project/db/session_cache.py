"""db/session_cache.py — Bounds server RAM under many users/chats.

Each chat's built retriever (FAISS index + BM25 index + chunk list) lives in
this process-wide LRU cache, capped at MAX_HOT_USERS entries. When a chat
that isn't currently "hot" becomes active, its documents are read back from
disk (see user_store.load_documents_chunks) and a fresh retriever is rebuilt
from them — cheap, since embeddings are already computed; it's just index
construction, not re-embedding.

Cache key: since a chat's retriever depends on WHICH documents it has
selected (not just who the user is), the key is a string built from the
sorted document IDs — two chats using the exact same documents share one
cached retriever; two chats with different document sets get their own.
"""
from collections import OrderedDict
import threading
from utils.logger import get_logger
from utils.timing import timed
from config.settings import MAX_HOT_USERS

logger = get_logger(__name__)

_lock = threading.Lock()
_hot: "OrderedDict[str, dict]" = OrderedDict()  # cache_key -> {"retriever":.., "chunks":.., ...}


def doc_ids_key(doc_ids) -> str:
    return "docs:" + ",".join(str(i) for i in sorted(doc_ids))


def _evict_if_needed():
    while len(_hot) > MAX_HOT_USERS:
        evicted_key, _ = _hot.popitem(last=False)  # oldest / least-recently-used
        logger.info(f"[session_cache] evicted '{evicted_key}' from RAM (data still safe on disk)")


def get_hot(key: str):
    with _lock:
        if key in _hot:
            _hot.move_to_end(key)
            return _hot[key]
    return None


def put_hot(key: str, bundle: dict):
    with _lock:
        _hot[key] = bundle
        _hot.move_to_end(key)
        _evict_if_needed()


def drop(key: str):
    with _lock:
        _hot.pop(key, None)


def drop_prefix(prefix: str):
    """Evict every hot entry whose key starts with prefix (e.g. clearing all
    of one user's cached chats when an admin deletes that user)."""
    with _lock:
        for k in [k for k in _hot if k.startswith(prefix)]:
            _hot.pop(k, None)


def hot_keys():
    with _lock:
        return list(_hot.keys())


def build_retriever_from_chunks(chunks, embedding_model: str, strategy: str,
                                reranking_enabled: bool, reranking_model: str):
    """Rebuild a full retriever (FAISS + BM25 + reranker) from already-embedded
    chunks — no re-embedding, so this is fast even for large chunk sets."""
    from embeddings.embedding_factory import EmbeddingFactory
    from indexing.hierarchical_index  import HierarchicalIndex
    from indexing.bm25_index          import BM25Index
    from retrieval.hybrid_retriever   import HybridRetriever
    from retrieval.reranker           import Reranker

    embedder = EmbeddingFactory(embedding_model).get_embedder()  # cached model, cheap to fetch
    with timed(f"session_cache.rebuild[{len(chunks)} chunks]"):
        h = HierarchicalIndex(); h.build(chunks)
        b = BM25Index();         b.build(chunks)
    retriever = HybridRetriever(h, b, embedder, strategy)
    reranker  = Reranker(reranking_enabled, reranking_model)
    return {"retriever": retriever, "reranker": reranker, "embedder": embedder, "chunks": chunks}


def get_or_rebuild(key: str, chunks, embedding_model: str, strategy: str,
                   reranking_enabled: bool, reranking_model: str):
    bundle = get_hot(key)
    if bundle is not None:
        return bundle
    bundle = build_retriever_from_chunks(chunks, embedding_model, strategy,
                                         reranking_enabled, reranking_model)
    put_hot(key, bundle)
    return bundle
