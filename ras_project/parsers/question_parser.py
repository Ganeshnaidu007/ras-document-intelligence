"""parsers/question_parser.py — Parse question documents into structured question lists."""
import re, json
from typing import List, Dict, Any
from utils.logger import get_logger
from config.prompts  import QUESTION_PARSE_SYSTEM, QUESTION_PARSE_USER
from config.settings import GOOGLE_API_KEY, OPENAI_API_KEY
logger = get_logger(__name__)

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash"]

PATTERNS = [
    re.compile(r"^(Q\d+|Question\s*\d+)[.:\)]\s*(.+)", re.IGNORECASE),
    re.compile(r"^(\d+)[.)\]]\s*(.+)"),
    re.compile(r"^([a-zA-Z][.)\]])\s*(.+)"),
    re.compile(r"^([ivxIVX]+)[.)\]]\s*(.+)"),
    re.compile(r"^[•\-\*]\s*(.+)"),
]


class QuestionParser:
    def parse(self, text: str) -> List[Dict[str, Any]]:
        questions = self._regex_parse(text)
        if not questions:
            questions = self._llm_parse(text)
        if not questions:
            questions = self._fallback(text)
        return questions

    def _regex_parse(self, text: str) -> List[Dict[str, Any]]:
        questions, lines, i = [], text.splitlines(), 0
        while i < len(lines):
            line = lines[i].strip()
            if not line: i += 1; continue
            matched = False
            for pat in PATTERNS:
                m = pat.match(line)
                if m:
                    groups = m.groups()
                    prefix = groups[0] if len(groups) > 1 else ""
                    q_text = groups[-1].strip()
                    i += 1
                    while i < len(lines) and lines[i].strip() and \
                            not any(p.match(lines[i].strip()) for p in PATTERNS):
                        q_text += " " + lines[i].strip(); i += 1
                    questions.append({
                        "number": re.sub(r"\D", "", prefix) if prefix else str(len(questions)+1),
                        "prefix": prefix, "text": q_text,
                    })
                    matched = True; break
            if not matched: i += 1
        return questions

    def _llm_parse(self, text: str) -> List[Dict[str, Any]]:
        try:
            prompt = QUESTION_PARSE_USER.format(text=text[:4000])
            if GOOGLE_API_KEY:
                return self._gemini_parse(prompt)
            if OPENAI_API_KEY:
                return self._openai_parse(prompt)
        except Exception as e:
            logger.warning(f"LLM question parse failed: {e}")
        return []

    def _gemini_parse(self, prompt: str) -> List[Dict[str, Any]]:
        from google import genai
        client = genai.Client(api_key=GOOGLE_API_KEY)
        last_err = None
        for m in GEMINI_MODELS:
            try:
                resp = client.models.generate_content(
                    model=m, contents=f"{QUESTION_PARSE_SYSTEM}\n\n{prompt}")
                raw = resp.text.strip().replace("```json","").replace("```","").strip()
                return json.loads(raw)
            except Exception as e:
                last_err = e
        raise RuntimeError(f"Gemini parse failed: {last_err}")

    def _openai_parse(self, prompt: str) -> List[Dict[str, Any]]:
        import openai
        resp = openai.OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
            model="gpt-4o-mini", max_tokens=1000, temperature=0,
            messages=[{"role": "system", "content": QUESTION_PARSE_SYSTEM},
                      {"role": "user",   "content": prompt}],
        )
        raw = resp.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        return json.loads(raw)

    def _fallback(self, text: str) -> List[Dict[str, Any]]:
        return [{"number": str(i), "prefix": str(i), "text": line.strip()}
                for i, line in enumerate(text.splitlines(), 1)
                if line.strip() and len(line.strip()) > 5]