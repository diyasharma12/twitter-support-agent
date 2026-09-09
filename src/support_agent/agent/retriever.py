"""Find historically similar customer messages, so a draft can be grounded in what this
brand actually did rather than in what an LLM imagines a brand would say.

Leakage is the thing to get right here. The retrieval corpus explicitly EXCLUDES every
thread_id in the golden set: otherwise the drafter would retrieve the very thread it is
being scored against and copy its reply, and the headline number would be fiction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Precedent:
    customer_message: str
    brand_reply: str
    score: float


class Retriever:
    """TF-IDF nearest neighbours over (customer message -> brand reply) pairs.

    TF-IDF rather than embeddings by default: it needs no API quota, is deterministic,
    and keeps `make eval` inside the 15-minute budget. Its weakness — it matches words,
    not meaning — is measured in the report rather than assumed away.
    """

    def __init__(self, corpus: list[dict]):
        self.corpus = [c for c in corpus if (c.get("brand_reply") or "").strip()]
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=2, max_features=20000
        )
        self.matrix = self.vectorizer.fit_transform(
            [c["customer_message"] for c in self.corpus]
        )

    @classmethod
    def from_sample(cls, sample_path: Path, exclude_ids: set) -> "Retriever":
        with open(sample_path, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        kept = [r for r in rows if str(r["thread_id"]) not in exclude_ids]
        return cls(kept)

    def search(self, message: str, k: int = 4) -> list[Precedent]:
        vec = self.vectorizer.transform([message])
        sims = cosine_similarity(vec, self.matrix)[0]
        top = sims.argsort()[::-1][:k]
        return [
            Precedent(
                customer_message=self.corpus[i]["customer_message"],
                brand_reply=self.corpus[i]["brand_reply"],
                score=float(sims[i]),
            )
            for i in top
            if sims[i] > 0
        ]
