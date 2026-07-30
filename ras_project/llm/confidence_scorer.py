"""llm/confidence_scorer.py — Self-rated answer confidence scoring.

Uses a tiny prompt (~150 tokens out) against the cheapest available model.
Runs SEQUENTIALLY (not in a thread pool) to avoid bursting the TPM limit
that is already under pressure from the main answer-generation pipeline.
"""
import json
from typing import List, Dict, Any
from utils.logger import get_logger
from config.settings import (GROQ_API_KEY, GOOGLE_API_KEY,
                               OPENROUTER_API_KEY, GROQ_MODELS, GEMINI_MODELS)
logger = get_logger(__name__)

SCORE_SYSTEM = (
    "You are an answer quality evaluator. "
    "Given a question, retrieved context, and a generated answer, "
    "return ONLY a JSON object like: "
    '{"score": 8, "reason": "Answer is fully supported by chunks 1 and 3."} '
    "Score 0-10: 0=completely unsupported, 5=partially supported, 10=fully grounded."
)


def _build_prompt(question: str, context: str, answer: str) -> str:
    return (
        f"Question: {question}\n\n"
        f"Context (retrieved chunks):\n{context[:2000]}\n\n"
        f"Generated answer:\n{answer[:800]}\n\n"
        'Return only JSON: {"score": N, "reason": "one sentence"}'
    )


def _call_llm(prompt: str) -> str:
    """
    Use the SAME cooldown-aware model tracker from react_agent so confidence
    scoring doesn't accidentally wake up a model that's in a 429 cooldown.
    Falls through providers from cheapest to most expensive.
    """
    # Reuse the process-level cooldown state from react_agent
    try:
        from agent.react_agent import _is_available, _set_cooldown, _dead_models, _parse_retry_delay
    except ImportError:
        # Fallback if import fails — no cooldown tracking
        _is_available = lambda m: True
        _set_cooldown  = lambda m, s: None
        _dead_models   = set()
        _parse_retry_delay = lambda e, default=10.0: default

    messages = [
        {"role": "system", "content": SCORE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]

    # ── Groq: use only the small/fast model to save TPM ──────────────────────
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            # Only try the 8b model for scoring — it's fast and cheap
            fast_models = [m for m in GROQ_MODELS if "8b" in m or "instant" in m]
            for m in fast_models:
                if not _is_available(m):
                    continue
                try:
                    resp = client.chat.completions.create(
                        model=m, max_tokens=120, temperature=0,
                        messages=messages)
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    err = str(e)
                    if "decommissioned" in err or "400" in err:
                        _dead_models.add(m)
                    elif "429" in err or "rate_limit" in err.lower():
                        delay = _parse_retry_delay(err, default=15.0)
                        _set_cooldown(m, delay)
                        logger.warning(f"Groq confidence {m}: 429 — cooldown {delay:.0f}s")
                    else:
                        logger.warning(f"Groq confidence {m}: {e}")
        except ImportError:
            pass

    # ── Gemini: use cheapest model ────────────────────────────────────────────
    if GOOGLE_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            for m in GEMINI_MODELS:   # already ordered cheapest-first in settings
                if not _is_available(m):
                    continue
                try:
                    resp = client.models.generate_content(
                        model=m, contents=f"{SCORE_SYSTEM}\n\n{prompt}")
                    return resp.text.strip()
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        from agent.react_agent import _parse_retry_delay as _prd
                        delay = _prd(err, default=45.0)
                        _set_cooldown(m, delay)
                    elif "503" in err:
                        _set_cooldown(m, 20.0)
                    logger.warning(f"Gemini confidence {m}: {e}")
        except Exception:
            pass

    # ── OpenRouter fallback ───────────────────────────────────────────────────
    if OPENROUTER_API_KEY:
        try:
            import openai
            client = openai.OpenAI(api_key=OPENROUTER_API_KEY,
                                   base_url="https://openrouter.ai/api/v1")
            resp = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=messages, max_tokens=120, temperature=0)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenRouter confidence: {e}")

    raise RuntimeError("No LLM available for confidence scoring")


def score_answer(question: str, chunks: List[Dict[str, Any]], answer: str) -> Dict[str, Any]:
    context = "\n\n".join(
        f"[{i+1}] {c.get('text','')[:300]}"
        for i, c in enumerate(chunks[:5])   # cap at 5 chunks to save tokens
    )
    try:
        raw  = _call_llm(_build_prompt(question, context, answer))
        raw  = raw.strip().replace("```json","").replace("```","").strip()
        data = json.loads(raw)
        score  = max(0, min(10, int(data.get("score", 5))))
        reason = data.get("reason", "")
    except Exception as e:
        logger.warning(f"Confidence scoring failed: {e}")
        score, reason = -1, "Scoring unavailable"

    if score >= 7:   label, color = "High",   "green"
    elif score >= 4: label, color = "Medium", "orange"
    elif score >= 0: label, color = "Low",    "red"
    else:            label, color = "N/A",    "gray"

    return {"score": score, "reason": reason, "label": label, "color": color}


def score_batch(questions_chunks_answers: List[tuple]) -> List[Dict[str, Any]]:
    """
    Score answers SEQUENTIALLY — NOT in a thread pool.

    Parallel confidence scoring causes a TPM spike on top of the main
    answer-generation pipeline which already used most of the per-minute quota.
    Sequential scoring adds ~0.3s per answer but eliminates cascading 429s.
    """
    results = []
    for q, c, a in questions_chunks_answers:
        try:
            results.append(score_answer(q, c, a))
        except Exception as e:
            logger.warning(f"score_batch item failed: {e}")
            results.append({"score": -1, "reason": "Unavailable", "label": "N/A", "color": "gray"})
    return results