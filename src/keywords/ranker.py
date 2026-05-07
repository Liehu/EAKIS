"""Keyword weight calculation: TF-IDF + DomainScore + RelevanceScore.

Wk = α × TF-IDF(k) + β × DomainScore(k) + γ × RelevanceScore(k)

Hyperparameters (tuned from historical samples):
  α = 0.35  (TF-IDF weight)
  β = 0.40  (domain relevance, highest to suppress generic words)
  γ = 0.25  (business relevance)
"""

from __future__ import annotations

import math
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

_DOMAIN_DIR = Path(__file__).parent / "domain_dicts"


@dataclass(frozen=True)
class KeywordCandidate:
    word: str
    keyword_type: str  # business | tech | entity
    tf_idf: float = 0.0
    domain_score: float = 0.0
    relevance_score: float = 0.0
    weight: float = 0.0
    confidence: float = 0.0
    source: str | None = None
    derived: bool = False
    parent_word: str | None = None


class DomainDictionary:
    """Loads and queries domain-specific word lists."""

    _FILE_MAP: dict[str, str] = {
        "security": "security.txt",
        "finance": "finance.txt",
        "fintech": "finance.txt",
        "ecommerce": "ecommerce.txt",
        "government": "government.txt",
        "healthcare": "healthcare.txt",
        "tech_stack": "tech_stack.txt",
    }

    def __init__(self, domains: list[str] | None = None) -> None:
        self._words: dict[str, set[str]] = {}
        all_domains = list(self._FILE_MAP.keys()) if domains is None else domains
        for d in all_domains:
            fname = self._FILE_MAP.get(d)
            if fname is None:
                continue
            fpath = _DOMAIN_DIR / fname
            if fpath.exists():
                self._words[d] = self._load(fpath)

    @staticmethod
    def _load(path: Path) -> set[str]:
        text = path.read_text(encoding="utf-8")
        tokens: set[str] = set()
        for line in text.splitlines():
            for tok in line.split(","):
                tok = tok.strip()
                if tok:
                    tokens.add(tok.lower())
        return tokens

    def score(self, word: str) -> float:
        """Return domain matching score in [0, 1]."""
        w = word.lower().strip()
        if not w:
            return 0.0
        match_count = sum(1 for s in self._words.values() if w in s)
        if not self._words:
            return 0.0
        # Exact match gets 1.0, partial match by substring gets lower score
        if match_count > 0:
            return min(1.0, match_count / max(len(self._words), 1) + 0.5)
        # Partial / substring match
        for domain_words in self._words.values():
            for dw in domain_words:
                if w in dw or dw in w:
                    return 0.3
        return 0.0


class TfIdfCalculator:
    """Simple TF-IDF over a collection of documents."""

    def __init__(self) -> None:
        self._doc_count = 0
        self._df: Counter[str] = Counter()

    def add_document(self, text: str) -> None:
        self._doc_count += 1
        seen: set[str] = set()
        for tok in self._tokenize(text):
            if tok not in seen:
                seen.add(tok)
                self._df[tok] += 1

    def tf_idf(self, word: str, text: str) -> float:
        tf = self._tf(word, text)
        idf = self._idf(word)
        return tf * idf

    def _tf(self, word: str, text: str) -> float:
        tokens = self._tokenize(text)
        if not tokens:
            return 0.0
        return tokens.count(word.lower()) / len(tokens)

    def _idf(self, word: str) -> float:
        if self._doc_count == 0:
            return 0.0
        df = self._df.get(word.lower(), 0)
        return math.log((self._doc_count + 1) / (df + 1)) + 1

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        # Simple whitespace + punctuation split; Chinese text handled via
        # the LLM-based extraction pipeline rather than token-level TF-IDF.
        return [t.lower() for t in text.replace(",", " ").replace(".", " ").replace("，", " ").replace("。", " ").split() if t.strip()]


class KeywordRanker:
    """Computes the composite weight for keyword candidates.

    Wk = α × TF-IDF(k) + β × DomainScore(k) + γ × RelevanceScore(k)
    """

    def __init__(
        self,
        domain: str | None = None,
        alpha: float = 0.35,
        beta: float = 0.40,
        gamma: float = 0.25,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        domains = [domain] if domain else None
        self._domain_dict = DomainDictionary(domains)
        self._tfidf = TfIdfCalculator()

    def add_reference_documents(self, texts: list[str]) -> None:
        for t in texts:
            self._tfidf.add_document(t)

    def compute_weight(
        self,
        word: str,
        tf_idf: float | None = None,
        domain_score: float | None = None,
        relevance_score: float | None = None,
        reference_text: str | None = None,
    ) -> float:
        if tf_idf is None:
            tf_idf = self._tfidf.tf_idf(word, reference_text or "")
        if domain_score is None:
            domain_score = self._domain_dict.score(word)
        if relevance_score is None:
            relevance_score = 0.5  # neutral default when LLM not available

        raw = self.alpha * tf_idf + self.beta * domain_score + self.gamma * relevance_score
        return min(1.0, max(0.0, raw))

    def rank(
        self,
        candidates: list[KeywordCandidate],
    ) -> list[KeywordCandidate]:
        ranked = []
        for c in candidates:
            w = self.compute_weight(
                c.word,
                tf_idf=c.tf_idf or None,
                domain_score=c.domain_score or None,
                relevance_score=c.relevance_score or None,
            )
            confidence = min(1.0, max(0.0, c.domain_score * 0.4 + c.relevance_score * 0.6))
            ranked.append(
                KeywordCandidate(
                    word=c.word,
                    keyword_type=c.keyword_type,
                    tf_idf=c.tf_idf,
                    domain_score=c.domain_score,
                    relevance_score=c.relevance_score,
                    weight=w,
                    confidence=confidence,
                    source=c.source,
                    derived=c.derived,
                    parent_word=c.parent_word,
                )
            )
        ranked.sort(key=lambda k: k.weight, reverse=True)
        return ranked
