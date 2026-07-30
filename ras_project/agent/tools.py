"""agent/tools.py — Tool registry for the Agentic RAG system.

Each tool is a callable that takes a string input and returns a string output.
The agent decides which tools to call, when, and in what order.
"""
from typing import Dict, Any
from utils.logger import get_logger
logger = get_logger(__name__)


TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {

    "retrieve_documents": {
        "description": (
            "Search the uploaded documents using hybrid semantic + BM25 retrieval. "
            "Use this when the question can be answered from the provided documents. "
            "Input: a specific search query string."
        ),
        "input_description": "A focused search query to retrieve relevant document chunks.",
    },

    "web_search": {
        "description": (
            "Search the web via SerpAPI for real-time or external information. "
            "Use when the question needs current data, context outside the documents, "
            "or verification of facts. Input: a search query string."
        ),
        "input_description": "A web search query to find external information.",
    },

    "read_url": {
        "description": (
            "Fetch and read the full content of a URL using Jina Reader. "
            "Use when web_search returns URLs that need deeper reading. "
            "Input: a valid URL string."
        ),
        "input_description": "A URL to fetch and extract full text content from.",
    },

    "refine_query": {
        "description": (
            "Rewrite or expand a query into better search terms. "
            "Use when initial retrieval returned weak results. "
            "Input: the original question or query."
        ),
        "input_description": "The query to rewrite into better search terms.",
    },

    "summarise_context": {
        "description": (
            "Compress and summarise a large body of retrieved context "
            "so it fits within the answer generation window. "
            "Use when you have too many chunks and need to condense them. "
            "Input: the raw text to summarise."
        ),
        "input_description": "Text to be summarised and compressed.",
    },

    "final_answer": {
        "description": (
            "Generate the final detailed answer from all gathered evidence. "
            "Call this ONLY when you have collected sufficient context. "
            "Input: the original user question."
        ),
        "input_description": "The original question to answer with all gathered context.",
    },
}


def tool_schema_for_llm() -> str:
    """Return tool descriptions formatted for the agent system prompt."""
    lines = []
    for name, meta in TOOL_REGISTRY.items():
        lines.append(f"- **{name}**: {meta['description']}")
    return "\n".join(lines)