"""ingestion/document_summarizer.py — Background auto-summary on upload.
Generates one concise summary + key topics per document, covering the
document's FULL text (not just a truncated opening excerpt, and not
retrieved/query-matched chunks — this runs once per upload, independent of
any question). Stored in session state for fast relevance pre-filtering."""
import threading
from typing import Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)

# Kept low: this only needs to gist one segment, not carry the whole
# summary — the FINAL synthesis step is what has to stay within budget,
# and it's built from these short partial notes, not from raw text.
_SEGMENT_CHARS   = 6000
_MAX_SEGMENTS    = 12          # hard cap so a huge document still finishes in bounded time
_PARTIAL_PROMPT  = """Summarise the key facts, numbers, and points in this excerpt from a \
larger document in 2-3 short sentences. Plain text only, no preamble.

Excerpt:
\"\"\"{text}\"\"\""""

_FINAL_PROMPT = """You were given short notes covering an ENTIRE document, section by \
section, in order. Combine them into ONE final summary of the whole document.

Document source: {source}
Section notes (in order):
{notes}

Return ONLY valid JSON:
{{
  "summary": "4-5 concise lines (a short paragraph) covering the document's overall \
purpose, main content, and key findings — not any single section.",
  "key_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "domain": "e.g. machine learning / legal / finance / medicine / history / general",
  "document_type": "e.g. research paper / report / contract / textbook / article"
}}

No explanation, no markdown fences, pure JSON only."""


def _llm_text(prompt: str, max_tokens: int) -> str:
    """One plain-text LLM call, Gemini first then Groq — same provider
    fallback used for the final JSON call below."""
    from config.settings import GOOGLE_API_KEY, GROQ_API_KEY

    if GOOGLE_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            resp = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
            return resp.text.strip()
        except Exception as e:
            logger.warning(f"Gemini call failed: {e}")

    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant", max_tokens=max_tokens, temperature=0.1,
                messages=[{"role": "user", "content": prompt}])
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq call failed: {e}")

    raise RuntimeError("No summarisation provider configured")


def _split_segments(text: str) -> List[str]:
    """Break the full document text into ordered segments covering all of
    it. Capped at _MAX_SEGMENTS — for a genuinely enormous document this
    samples evenly across the whole length rather than just the start, so
    the summary still reflects beginning, middle, and end."""
    if not text:
        return []
    n = max(1, -(-len(text) // _SEGMENT_CHARS))   # ceil division
    if n <= _MAX_SEGMENTS:
        return [text[i:i+_SEGMENT_CHARS] for i in range(0, len(text), _SEGMENT_CHARS)]
    # Too many segments to summarise individually within a reasonable time —
    # take _MAX_SEGMENTS evenly-spaced windows spanning the full document.
    step = len(text) / _MAX_SEGMENTS
    return [text[int(i*step):int(i*step)+_SEGMENT_CHARS] for i in range(_MAX_SEGMENTS)]


def _call_llm_summary(source: str, text: str) -> Dict[str, Any]:
    """Map-reduce over the WHOLE document: summarise each segment briefly,
    then combine every segment's notes into one final, concise summary —
    so long documents are actually covered end to end, not just their
    opening excerpt."""
    import json, re

    segments = _split_segments(text)
    if not segments:
        return {"summary": "", "key_topics": [], "domain": "general", "document_type": "document"}

    notes = []
    for seg in segments:
        try:
            notes.append(_llm_text(_PARTIAL_PROMPT.format(text=seg), max_tokens=120))
        except Exception as e:
            logger.warning(f"Segment summary failed for {source}: {e}")
    if not notes:
        return {
            "summary": text[:400].strip() + ("..." if len(text) > 400 else ""),
            "key_topics": [], "domain": "general", "document_type": "document",
        }

    numbered_notes = "\n".join(f"{i+1}. {n}" for i, n in enumerate(notes))
    final = _llm_text(_FINAL_PROMPT.format(source=source, notes=numbered_notes), max_tokens=350)
    raw = re.sub(r"```json|```", "", final).strip()
    return json.loads(raw)


def summarize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronously summarize a parsed document — using its full text,
    not a single truncated excerpt and not retrieval-matched chunks."""
    source = doc.get("source", "unknown")
    all_text = "\n".join(p.get("text", "") for p in doc.get("pages", []))

    try:
        result = _call_llm_summary(source, all_text)
        result["source"] = source
        result["char_count"] = len(all_text)
        return result
    except Exception as e:
        logger.error(f"Summary failed for {source}: {e}")
        return {
            "source": source,
            "summary": all_text[:400].strip() + ("..." if len(all_text) > 400 else ""),
            "key_topics": [],
            "domain": "general",
            "document_type": "document",
            "char_count": len(all_text),
        }


def summarize_documents_async(docs: List[Dict[str, Any]],
                               callback=None) -> threading.Thread:
    """
    Start background summarization of all documents.
    When done, calls callback(summaries: list) if provided.
    """
    def _worker():
        summaries = []
        for doc in docs:
            summary = summarize_document(doc)
            summaries.append(summary)
            logger.info(f"Summarized: {summary.get('source', '?')}")
        if callback:
            try:
                callback(summaries)
            except Exception as e:
                logger.error(f"Summary callback failed: {e}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t



