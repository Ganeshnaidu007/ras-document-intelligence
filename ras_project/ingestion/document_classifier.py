"""ingestion/document_classifier.py — Auto-detects document type and returns
optimal chunking + embedding settings via a quick Gemini/Groq LLM call."""
import json
import re
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

# Decision table: doc_type -> (chunking_method, chunk_size, overlap, embedding_model)
CLASSIFICATION_TABLE: Dict[str, Dict[str, Any]] = {
    "research_paper": {
        "chunking_method": "Semantic + Recursive Hybrid",
        "chunk_size": 400,
        "chunk_overlap": 50,
        "embedding_model": "OpenAI text-embedding-3-small",
        "fallback_embedding": "all-MiniLM-L6-v2",
    },
    "legal_document": {
        "chunking_method": "Paragraph Chunking",
        "chunk_size": 600,
        "chunk_overlap": 80,
        "embedding_model": "OpenAI text-embedding-3-small",
        "fallback_embedding": "all-MiniLM-L6-v2",
    },
    "financial_report": {
        "chunking_method": "Recursive Chunking",
        "chunk_size": 500,
        "chunk_overlap": 60,
        "embedding_model": "OpenAI text-embedding-3-small",
        "fallback_embedding": "all-MiniLM-L6-v2",
    },
    "code": {
        "chunking_method": "Fixed Chunking",
        "chunk_size": 200,
        "chunk_overlap": 20,
        "embedding_model": "all-MiniLM-L6-v2",
        "fallback_embedding": "all-MiniLM-L6-v2",
    },
    "narrative_text": {
        "chunking_method": "Semantic Chunking",
        "chunk_size": 700,
        "chunk_overlap": 100,
        "embedding_model": "all-MiniLM-L6-v2",
        "fallback_embedding": "all-MiniLM-L6-v2",
    },
    "multilingual": {
        "chunking_method": "Semantic + Recursive Hybrid",
        "chunk_size": 400,
        "chunk_overlap": 50,
        "embedding_model": "Jina embeddings-v3",
        "fallback_embedding": "multilingual-e5",
    },
    "short_snippets": {
        "chunking_method": "Sentence Chunking",
        "chunk_size": 200,
        "chunk_overlap": 20,
        "embedding_model": "all-MiniLM-L6-v2",
        "fallback_embedding": "all-MiniLM-L6-v2",
    },
    "general": {
        "chunking_method": "Semantic + Recursive Hybrid",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "embedding_model": "all-MiniLM-L6-v2",
        "fallback_embedding": "all-MiniLM-L6-v2",
    },
}

CLASSIFY_PROMPT = """You are a document analysis expert. Read the following sample text (first ~500 chars of a document) and classify it.

Sample:
\"\"\"
{sample}
\"\"\"

Return ONLY valid JSON with these exact keys:
{{
  "doc_type": "<one of: research_paper, legal_document, financial_report, code, narrative_text, multilingual, short_snippets, general>",
  "language": "<primary language, e.g. English, Hindi, mixed>",
  "is_technical": <true or false>,
  "confidence": <0.0-1.0>
}}

No explanation, no markdown, no backticks. Pure JSON only."""


def _llm_classify(sample: str) -> Dict[str, Any]:
    """Call LLM (Gemini Flash preferred, Groq fallback) to classify document."""
    from config.settings import GOOGLE_API_KEY, GROQ_API_KEY

    prompt = CLASSIFY_PROMPT.format(sample=sample[:500])

    # Try Gemini first (fastest for short tasks)
    if GOOGLE_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            resp = client.models.generate_content(
                model="gemini-2.0-flash-lite", contents=prompt
            )
            raw = resp.text.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Gemini classify failed: {e}")

    # Groq fallback
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                max_tokens=200,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Groq classify failed: {e}")

    return {"doc_type": "general", "language": "English", "is_technical": False, "confidence": 0.0}


def _heuristic_classify(sample: str) -> Dict[str, Any]:
    """Fast regex-based fallback classifier."""
    s = sample.lower()
    if any(k in s for k in ["abstract", "arxiv", "doi:", "methodology", "introduction\n"]):
        return {"doc_type": "research_paper", "language": "English", "is_technical": True, "confidence": 0.7}
    if any(k in s for k in ["whereas", "hereinafter", "section", "clause", "plaintiff", "defendant"]):
        return {"doc_type": "legal_document", "language": "English", "is_technical": False, "confidence": 0.7}
    if any(k in s for k in ["revenue", "fiscal", "earnings per share", "balance sheet", "q1", "q2"]):
        return {"doc_type": "financial_report", "language": "English", "is_technical": True, "confidence": 0.7}
    if re.search(r"def |class |import |function\(|<html|{\"key\"", s):
        return {"doc_type": "code", "language": "English", "is_technical": True, "confidence": 0.8}
    # Detect non-ASCII (multilingual)
    non_ascii = sum(1 for c in sample if ord(c) > 127)
    if non_ascii / max(len(sample), 1) > 0.1:
        return {"doc_type": "multilingual", "language": "mixed", "is_technical": False, "confidence": 0.6}
    return {"doc_type": "general", "language": "English", "is_technical": False, "confidence": 0.5}


def classify_document(doc: Dict[str, Any], use_llm: bool = True) -> Dict[str, Any]:
    """
    Main entry point. Takes a parsed doc dict, returns recommended settings.

    Returns:
        {
            "doc_type": str,
            "language": str,
            "is_technical": bool,
            "chunking_method": str,
            "chunk_size": int,
            "chunk_overlap": int,
            "embedding_model": str,
            "classification_source": "llm" | "heuristic",
        }
    """
    # Extract sample from first 2 pages
    sample_parts = []
    for page in doc.get("pages", [])[:2]:
        sample_parts.append(page.get("text", "")[:300])
    sample = "\n".join(sample_parts)[:600]

    if not sample.strip():
        logger.warning("Empty sample — using general defaults")
        settings = CLASSIFICATION_TABLE["general"].copy()
        settings.update({"doc_type": "general", "language": "English",
                         "is_technical": False, "classification_source": "default"})
        return settings

    # Try LLM classification first, then heuristic fallback
    if use_llm:
        try:
            result = _llm_classify(sample)
            source = "llm"
        except Exception:
            result = _heuristic_classify(sample)
            source = "heuristic"
    else:
        result = _heuristic_classify(sample)
        source = "heuristic"

    doc_type = result.get("doc_type", "general")
    if doc_type not in CLASSIFICATION_TABLE:
        doc_type = "general"

    table_entry = CLASSIFICATION_TABLE[doc_type].copy()

    # Override embedding if no API keys available
    from config.settings import OPENAI_API_KEY, JINA_API_KEY
    preferred = table_entry["embedding_model"]
    if "openai" in preferred.lower() and not OPENAI_API_KEY:
        table_entry["embedding_model"] = table_entry["fallback_embedding"]
    if "jina" in preferred.lower() and not JINA_API_KEY:
        table_entry["embedding_model"] = table_entry["fallback_embedding"]

    # Remove internal key
    table_entry.pop("fallback_embedding", None)

    return {
        **table_entry,
        "doc_type": doc_type,
        "language": result.get("language", "English"),
        "is_technical": result.get("is_technical", False),
        "classification_confidence": result.get("confidence", 0.0),
        "classification_source": source,
    }
