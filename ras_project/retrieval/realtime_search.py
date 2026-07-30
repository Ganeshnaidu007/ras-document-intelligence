"""retrieval/realtime_search.py — SerpAPI search + Jina Reader for full page content."""
import json, urllib.request, urllib.parse
from typing import List, Dict, Any
from utils.logger import get_logger
from config.settings import (SERP_API_KEY, SERP_API_URL, SERP_ENGINE,
                               GOOGLE_API_KEY, JINA_API_KEY, GEMINI_MODELS)
logger = get_logger(__name__)


class RealTimeSearcher:

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Fetch SerpAPI results. Returns list of {title, link, snippet}."""
        if not SERP_API_KEY:
            logger.error("SERP_API_KEY not set in secrets.toml"); return []
        params = urllib.parse.urlencode({
            "q": query, "api_key": SERP_API_KEY,
            "engine": SERP_ENGINE, "num": num_results,
        })
        try:
            with urllib.request.urlopen(f"{SERP_API_URL}?{params}", timeout=15) as r:
                data = json.loads(r.read())
            results = [
                {"title":   i.get("title", ""),
                 "link":    i.get("link", ""),
                 "snippet": i.get("snippet", "")}
                for i in data.get("organic_results", [])[:num_results]
            ]
            logger.info(f"SerpAPI: {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(f"SerpAPI error: {e}"); return []

    def _jina_read(self, url: str) -> str:
        """Fetch full page content via Jina Reader — returns clean markdown text."""
        if not JINA_API_KEY:
            return ""
        try:
            req = urllib.request.Request(
                f"https://r.jina.ai/{url}",
                headers={
                    "Authorization":   f"Bearer {JINA_API_KEY}",
                    "Accept":          "application/json",
                    "X-Return-Format": "markdown",
                })
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            content = data.get("data", {}).get("content", "")
            return content[:4000]  # cap to avoid massive context
        except Exception as e:
            logger.warning(f"Jina Reader ({url}): {e}")
            return ""

    def to_chunks(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch search results and, if Jina key is present, read the full page
        content for each URL — much richer than just snippets.
        """
        import concurrent.futures, uuid
        results = self.search(query, num_results)
        chunks  = []

        def _process(i_r):
            i, r = i_r
            # Try Jina Reader for full content; fall back to snippet
            full_text = self._jina_read(r["link"]) if JINA_API_KEY else ""
            text = full_text if len(full_text) > 200 else f"{r['title']}. {r['snippet']}"
            source_label = "Jina Reader" if full_text else "SerpAPI snippet"
            return {
                "chunk_id":       str(uuid.uuid4())[:8],
                "text":           text,
                "source":         r["link"],
                "page_number":    f"web-{i+1}",
                "chunk_index":    i,
                "author":         source_label,
                "parent_section": r["title"],
                "language":       "",
                "semantic_tags":  [],
                "token_count":    len(text.split()),
                "embedding":      None,
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            chunks = list(ex.map(_process, enumerate(results)))

        logger.info(f"RealTimeSearcher: {len(chunks)} chunks "
                    f"({'Jina Reader' if JINA_API_KEY else 'snippets only'})")
        return chunks

    def search_and_summarise(self, query: str, num_results: int = 5) -> str:
        """Fetch results, read full pages, summarise with Gemini."""
        chunks = self.to_chunks(query, num_results)
        if not chunks:
            return "No real-time results found."
        combined = "\n\n".join(
            f"[{i+1}] Source: {c['source']}\n{c['text'][:600]}"
            for i, c in enumerate(chunks)
        )
        if not GOOGLE_API_KEY:
            return combined
        prompt = (
            f"Based on these real-time web results, answer: '{query}'\n\n"
            f"{combined}\n\nProvide a concise factual answer with source references."
        )
        try:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            for m in GEMINI_MODELS:
                try:
                    return client.models.generate_content(model=m, contents=prompt).text.strip()
                except Exception as e:
                    logger.warning(f"Gemini summarise {m}: {e}")
        except Exception as e:
            logger.error(f"Gemini summarise failed: {e}")
        return combined