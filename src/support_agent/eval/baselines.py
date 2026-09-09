"""Two baselines, because a number with nothing to beat is not evidence.

TrivialBaseline  — the cheapest thing that could possibly be shipped: always predict the
                   most common intent, always escalate, always send the same template.
                   Its job is to expose how much of the headline accuracy is just class
                   imbalance.
SimpleBaseline   — the strongest thing that uses no LLM at all: TF-IDF + logistic
                   regression for intent, nearest-neighbour retrieval for the reply,
                   the same rule-based escalation policy. Its job is to answer "does the
                   LLM actually earn its cost and latency?"
"""
from __future__ import annotations

from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from ..agent.escalation import decide
from ..agent.retriever import Retriever

TEMPLATE = (
    "We're sorry for the trouble. Please DM us your confirmation number and we'll "
    "take a look."
)


class TrivialBaseline:
    name = "trivial"

    def fit(self, messages: list[str], intents: list[str]) -> "TrivialBaseline":
        self.majority = Counter(intents).most_common(1)[0][0]
        return self

    def handle(self, message: str) -> dict:
        return {
            "intent": self.majority,
            "confidence": 1.0,
            "decision": "escalate",
            "reason": "trivial baseline always escalates",
            "reply": TEMPLATE,
        }


class SimpleBaseline:
    name = "simple"

    def __init__(self, retriever: Retriever):
        self.retriever = retriever

    def fit(self, messages: list[str], intents: list[str]) -> "SimpleBaseline":
        self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        X = self.vec.fit_transform(messages)
        self.clf = LogisticRegression(max_iter=1000, class_weight="balanced").fit(
            X, intents
        )
        return self

    def handle(self, message: str) -> dict:
        X = self.vec.transform([message])
        intent = self.clf.predict(X)[0]
        confidence = float(self.clf.predict_proba(X).max())
        call = decide(message, intent, confidence)
        hits = self.retriever.search(message, k=1)
        return {
            "intent": intent,
            "confidence": confidence,
            "decision": call.decision,
            "reason": call.reason,
            "reply": hits[0].brand_reply if hits else TEMPLATE,
        }
