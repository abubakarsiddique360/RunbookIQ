"""A compact BM25 index over runbooks."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from runbookiq.kb import Runbook

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORD_TEXT = (
    "a an and are as at be by for from has have how i if in into is it of on or that the "
    "this to was what when where which with you your"
)
STOPWORDS = frozenset(_STOPWORD_TEXT.split())


def tokenize(text: str) -> list[str]:
    return [word for word in _TOKEN_RE.findall(text.lower()) if word not in STOPWORDS]


@dataclass(frozen=True)
class Hit:
    runbook: Runbook
    score: float
    matched: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "id": self.runbook.id,
            "title": self.runbook.title,
            "score": round(self.score, 3),
            "matched": list(self.matched),
        }


class RunbookIndex:
    """Okapi BM25 (k1=1.5, b=0.75) over runbook text."""

    def __init__(self, runbooks: list[Runbook], k1: float = 1.5, b: float = 0.75) -> None:
        self.runbooks = runbooks
        self.k1 = k1
        self.b = b
        self.docs = [Counter(tokenize(runbook.searchable)) for runbook in runbooks]
        self.lengths = [sum(doc.values()) for doc in self.docs]
        self.avg = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        self.df: Counter[str] = Counter()
        for doc in self.docs:
            self.df.update(doc.keys())

    def _idf(self, term: str) -> float:
        total = len(self.docs)
        df = self.df.get(term, 0)
        return math.log(1 + (total - df + 0.5) / (df + 0.5))

    def search(self, query: str, limit: int = 3, min_score: float = 0.1) -> list[Hit]:
        terms = tokenize(query)
        if not terms or not self.docs:
            return []
        scored: list[Hit] = []
        for index, doc in enumerate(self.docs):
            score = 0.0
            matched: list[str] = []
            length = self.lengths[index] or 1
            norm = self.k1 * (1 - self.b + self.b * length / (self.avg or 1))
            for term in dict.fromkeys(terms):
                freq = doc.get(term, 0)
                if not freq:
                    continue
                score += self._idf(term) * (freq * (self.k1 + 1)) / (freq + norm)
                matched.append(term)
            if score > 0:
                scored.append(
                    Hit(runbook=self.runbooks[index], score=score, matched=tuple(matched))
                )
        scored.sort(key=lambda hit: hit.score, reverse=True)
        if not scored:
            return []
        best = scored[0].score
        return [hit for hit in scored if hit.score >= max(min_score, best * 0.25)][:limit]
