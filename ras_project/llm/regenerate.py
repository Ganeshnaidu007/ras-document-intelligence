"""llm/regenerate.py — 'Try again with different settings' for one Q&A.

Deliberately does NOT re-run retrieval or the ReAct reasoning loop — it
re-generates the answer from the SAME already-retrieved chunks using a
different LLM provider. That keeps a regeneration to a single LLM call
(fast) while still giving a genuinely different answer to compare against,
instead of paying the full multi-iteration agent cost again.
"""
from typing import List, Dict, Any
from config.settings import GROQ_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY
from utils.logger import get_logger
logger = get_logger(__name__)

PROVIDER_ORDER = ["groq", "gemini", "openrouter", "openai"]
_KEYS = {"groq": GROQ_API_KEY, "gemini": GOOGLE_API_KEY,
         "openrouter": OPENROUTER_API_KEY, "openai": OPENAI_API_KEY}


def available_providers() -> List[str]:
    return [p for p in PROVIDER_ORDER if _KEYS.get(p)] or list(PROVIDER_ORDER)


def next_provider(current: str, tried: List[str]) -> str:
    """Prefer a provider that hasn't been tried yet on this question. Once
    every available provider has had a turn, cycle back through them
    (never immediately repeating whichever just ran)."""
    avail = available_providers()
    untried = [p for p in avail if p not in tried]
    if untried:
        return untried[0]
    others = [p for p in avail if p != current] or avail
    return others[len(tried) % len(others)]


def regenerate(question: str, chunks: List[Dict[str, Any]], tried_providers: List[str],
               current_provider: str, response_style: str = "concise") -> Dict[str, Any]:
    """Returns {"answer", "provider", "confidence"} for a fresh attempt at
    this question, on a different model than `current_provider`."""
    from llm.answer_generator import AnswerGenerator
    provider = next_provider(current_provider, tried_providers)
    gen = AnswerGenerator(provider=provider, response_style=response_style)
    answer = gen.generate(question, chunks)

    confidence = None
    try:
        from llm.confidence_scorer import score_answer
        confidence = score_answer(question, chunks, answer)
    except Exception as e:
        logger.warning(f"Regenerate: confidence scoring skipped: {e}")

    return {"answer": answer, "provider": provider, "confidence": confidence}
