"""llm/fact_checker.py — Post-generation fact-checking loop.
Checks every factual claim in the answer against the retrieved chunks.
Returns a list of {claim, supported, source, quote} dicts shown in 
an expandable verification panel."""
import json
import re
from typing import List, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

FACT_CHECK_PROMPT = """You are a rigorous fact-checker. You have an answer and the source chunks it was supposedly based on.

## Source Chunks
{chunks}

## Answer to Verify
{answer}

## Task
Extract every distinct factual claim from the answer (ignore filler phrases). For each claim, check whether the source chunks support it.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "claims": [
    {{
      "claim": "The exact factual claim in 1-2 sentences",
      "supported": true,
      "source": "filename or 'Not in sources'",
      "page": "page number or null",
      "quote": "Exact supporting text from chunks (max 100 chars) or null if not supported"
    }}
  ]
}}

Rules:
- Only extract checkable facts (names, numbers, dates, relationships, definitions)
- Mark as supported=false if the claim cannot be verified from the chunks
- Be strict: paraphrased content counts as supported, hallucinated details do not
- Extract 3-8 claims maximum"""


def _format_chunks_for_check(chunks: List[Dict[str, Any]], max_chars: int = 3000) -> str:
    parts = []
    total = 0
    for i, c in enumerate(chunks[:8]):
        src = c.get("source", "?")
        pg = c.get("page_number", "?")
        text = c.get("text", "")[:400]
        part = f"[{i+1}] {src} p.{pg}: {text}"
        total += len(part)
        if total > max_chars:
            break
        parts.append(part)
    return "\n\n".join(parts)


def fact_check_answer(answer: str, chunks: List[Dict[str, Any]],
                      provider: str = "groq") -> List[Dict[str, Any]]:
    """
    Run a fact-checking pass on the answer against retrieved chunks.
    
    Returns:
        List of claim dicts: [{claim, supported, source, page, quote}]
    """
    if not chunks or not answer:
        return []

    chunks_text = _format_chunks_for_check(chunks)
    prompt = FACT_CHECK_PROMPT.format(
        chunks=chunks_text,
        answer=answer[:2000],
    )

    raw = _call_llm(prompt, provider)
    if not raw:
        return []

    try:
        raw = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        claims = data.get("claims", [])
        # Ensure all required keys
        result = []
        for c in claims:
            result.append({
                "claim": c.get("claim", ""),
                "supported": bool(c.get("supported", True)),
                "source": c.get("source", "Unknown"),
                "page": c.get("page"),
                "quote": c.get("quote"),
            })
        return result
    except Exception as e:
        logger.warning(f"Fact-check JSON parse failed: {e}  raw={raw[:200]}")
        return []


def _call_llm(prompt: str, provider: str) -> str:
    from config.settings import GROQ_API_KEY, GOOGLE_API_KEY, GROQ_MODELS

    if provider == "groq" and GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            for m in GROQ_MODELS[:2]:
                try:
                    resp = client.chat.completions.create(
                        model=m, max_tokens=800, temperature=0.0,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    logger.warning(f"Groq fact-check {m}: {e}")
        except ImportError:
            pass

    if GOOGLE_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            resp = client.models.generate_content(
                model="gemini-2.0-flash-lite", contents=prompt
            )
            return resp.text.strip()
        except Exception as e:
            logger.warning(f"Gemini fact-check: {e}")

    return ""


def render_fact_check_panel(claims: List[Dict[str, Any]]) -> None:
    """Render an expandable Streamlit verification panel."""
    import streamlit as st

    if not claims:
        return

    supported = sum(1 for c in claims if c.get("supported"))
    total = len(claims)
    pct = int(supported / total * 100) if total > 0 else 0

    color = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")

    with st.expander(
        f"{color} **Fact Verification** — {supported}/{total} claims supported ({pct}%)",
        expanded=False
    ):
        for i, c in enumerate(claims, 1):
            icon = "✅" if c.get("supported") else "❌"
            st.markdown(f"**{icon} Claim {i}:** {c.get('claim', '')}")
            if c.get("supported"):
                src = c.get("source", "")
                pg = c.get("page", "")
                quote = c.get("quote", "")
                loc = f"`{src}`" + (f" · p.{pg}" if pg else "")
                st.caption(f"Source: {loc}")
                if quote:
                    st.caption(f"> {quote}")
            else:
                st.caption("⚠️ Not found in retrieved chunks — may be hallucinated")
            if i < len(claims):
                st.divider()
