"""retrieval/semantic_cache.py — Session-level semantic cache for answers.
Before running the full pipeline, embed the question and check if a 
semantically similar question was already answered this session.
"""
import re
import difflib
import numpy as np
from typing import Optional, Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)

# Was 0.92 — too loose. Two short questions that share almost every word
# except one distinguishing term ("What does the policy say about
# bribery?" vs "...about a bribe?") can score well above 0.92 on MiniLM
# even though the intended answer is different (one asks about the
# offence/pattern of conduct, the other about a specific payment). That
# was causing wrong cached answers to come back for genuinely different
# questions. 0.97 requires near-paraphrase-level similarity instead.
COSINE_THRESHOLD = 0.97

# Second gate, independent of the embedding: the two question STRINGS also
# need to be largely the same words in the same order (not just similar
# in vector space). This is what actually catches "bribery" vs "bribe" —
# they're different literal tokens, so word-level similarity drops even
# when the sentence-level cosine similarity stays high.
WORD_OVERLAP_THRESHOLD = 0.75


def _cosine(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype="float32")
    vb = np.array(b, dtype="float32")
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _word_similarity(a: str, b: str) -> float:
    """Literal word-level similarity, case-insensitive, ignoring
    punctuation — a cheap but effective guard against embedding
    near-misses between related-but-distinct terms."""
    norm = lambda s: re.sub(r"[^\w\s]", "", s.lower()).split()
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


class SemanticCache:
    """
    Stores (question_embedding, answer_dict) pairs for the session.
    Lookup: embed new question, find nearest cached question by cosine similarity.
    """

    def __init__(self, threshold: float = COSINE_THRESHOLD):
        self.threshold = threshold
        self._entries: List[Dict[str, Any]] = []  # {embedding, question, answer_data}
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from embeddings.local_embeddings import _load_model
                self._embedder = _load_model("all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"SemanticCache: failed to load embedder: {e}")
        return self._embedder

    def _embed(self, text: str) -> Optional[List[float]]:
        embedder = self._get_embedder()
        if embedder is None:
            return None
        try:
            vec = embedder.encode([text], show_progress_bar=False, convert_to_numpy=True)
            return vec[0].tolist()
        except Exception as e:
            logger.warning(f"SemanticCache embed error: {e}")
            return None

    def lookup(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Check if a semantically similar question was already answered.
        Requires BOTH a high embedding similarity AND high literal word
        overlap with the cached question — cosine alone let closely
        related-but-different terms (bribery/bribe, contract/agreement,
        etc.) match each other and return the wrong cached answer.
        Returns the cached answer_data dict or None.
        """
        if not self._entries:
            return None

        q_vec = self._embed(question)
        if q_vec is None:
            return None

        best_score = 0.0
        best_entry = None

        for entry in self._entries:
            score = _cosine(q_vec, entry["embedding"])
            if score > best_score:
                best_score = score
                best_entry = entry

        if (best_score >= self.threshold and best_entry
                and _word_similarity(question, best_entry["question"]) >= WORD_OVERLAP_THRESHOLD):
            logger.info(f"SemanticCache HIT (cosine={best_score:.3f}): "
                        f"'{best_entry['question'][:60]}'")
            return {**best_entry["answer_data"], "_cache_hit": True,
                    "_cache_score": round(best_score, 4),
                    "_cache_original": best_entry["question"]}

        return None

    def store(self, question: str, answer_data: Dict[str, Any]) -> None:
        """Store a question + answer in the cache."""
        q_vec = self._embed(question)
        if q_vec is None:
            return
        self._entries.append({
            "embedding": q_vec,
            "question": question,
            "answer_data": answer_data,
        })
        logger.info(f"SemanticCache stored: '{question[:60]}' "
                    f"(total entries: {len(self._entries)})")

    def clear(self) -> None:
        self._entries.clear()
        logger.info("SemanticCache cleared")

    def stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._entries),
            "threshold": self.threshold,
            "questions": [e["question"][:60] for e in self._entries],
        }
