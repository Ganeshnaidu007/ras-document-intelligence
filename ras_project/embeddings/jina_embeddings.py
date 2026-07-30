"""embeddings/jina_embeddings.py — Jina AI embeddings + Jina Reader for URL ingestion."""
import json, urllib.request, urllib.error
from typing import List, Dict, Any
from utils.logger import get_logger
from config.settings import JINA_API_KEY, JINA_EMBED_URL, JINA_READER_URL, JINA_EMBED_MODEL
logger = get_logger(__name__)


class JinaEmbedder:
    """Jina embeddings-v3 — 8192 token context, 1024 dims, multilingual."""

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts: return []
        if not JINA_API_KEY:
            logger.error("JINA_API_KEY not set in secrets.toml")
            return [[0.0] * 1024] * len(texts)
        # Jina allows max 2048 chars per text — truncate gracefully
        safe = [t[:2000] for t in texts]
        payload = json.dumps({
            "model":           JINA_EMBED_MODEL,
            "input":           safe,
            "task":            "retrieval.passage",
            "late_chunking":   False,
            "dimensions":      1024,
            "embedding_type":  "float",
        }).encode()
        req = urllib.request.Request(
            JINA_EMBED_URL, data=payload, method="POST",
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {JINA_API_KEY}",
            })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            logger.error(f"Jina embed error: {e}")
            return [[0.0] * 1024] * len(texts)

    def embed_single(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_query(self, text: str) -> List[float]:
        """Use retrieval.query task type for queries (better accuracy)."""
        if not JINA_API_KEY:
            return [0.0] * 1024
        payload = json.dumps({
            "model":          JINA_EMBED_MODEL,
            "input":          [text[:2000]],
            "task":           "retrieval.query",
            "dimensions":     1024,
            "embedding_type": "float",
        }).encode()
        req = urllib.request.Request(
            JINA_EMBED_URL, data=payload, method="POST",
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {JINA_API_KEY}",
            })
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Jina query embed error: {e}")
            return [0.0] * 1024


class JinaReader:
    """Jina Reader — converts any URL to clean markdown for ingestion."""

    def read_url(self, url: str) -> Dict[str, Any]:
        """Fetch and clean a web page. Returns {url, title, text, tokens}."""
        if not JINA_API_KEY:
            logger.error("JINA_API_KEY not set in secrets.toml")
            return {"url": url, "title": "", "text": "", "tokens": 0}
        target = JINA_READER_URL + url
        req = urllib.request.Request(
            target, method="GET",
            headers={
                "Authorization": f"Bearer {JINA_API_KEY}",
                "Accept":        "application/json",
                "X-Return-Format": "markdown",
            })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
            result = data.get("data", {})
            text   = result.get("content", result.get("text", ""))
            title  = result.get("title", url)
            logger.info(f"Jina Reader: {url} → {len(text)} chars")
            return {
                "url":    url,
                "title":  title,
                "text":   text,
                "tokens": len(text.split()),
            }
        except Exception as e:
            logger.error(f"Jina Reader error ({url}): {e}")
            return {"url": url, "title": "", "text": "", "tokens": 0}

    def read_urls_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Read multiple URLs. Falls back gracefully on individual errors."""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            return list(ex.map(self.read_url, urls))

    def to_chunks(self, url: str) -> List[Dict[str, Any]]:
        """Read a URL and return it as RAG-compatible chunks."""
        import uuid
        result = self.read_url(url)
        if not result["text"]:
            return []
        # Split into ~500-word paragraphs
        paragraphs = [p.strip() for p in result["text"].split("\n\n") if p.strip()]
        chunks = []
        for i, para in enumerate(paragraphs):
            if len(para.split()) < 10:
                continue
            chunks.append({
                "chunk_id":       str(uuid.uuid4())[:8],
                "text":           para,
                "source":         url,
                "page_number":    f"web-{i+1}",
                "chunk_index":    i,
                "author":         "Jina Reader",
                "parent_section": result["title"],
                "language":       "",
                "semantic_tags":  [],
                "token_count":    len(para.split()),
                "embedding":      None,
            })
        return chunks