"""The agent: classify -> retrieve -> draft -> decide.

Kept as one small readable function so the whole system fits in your head. Every stage's
intermediate output is returned, because the failure analysis needs to attribute a bad
reply to the stage that caused it (wrong intent vs bad retrieval vs bad drafting).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..llm import LLM
from .classifier import IntentClassifier
from .drafter import ReplyDrafter
from .escalation import decide
from .retriever import Retriever


@dataclass
class AgentOutput:
    message: str
    intent: str
    confidence: float
    decision: str
    reason: str
    reply: str
    precedents: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class SupportAgent:
    def __init__(self, retriever: Retriever, cfg: dict, llm: LLM | None = None):
        self.cfg = cfg
        self.llm = llm or LLM(cfg)
        self.retriever = retriever
        self.classifier = IntentClassifier(self.llm, cfg)
        self.drafter = ReplyDrafter(self.llm, cfg)

    def handle(self, message: str, k: int = 4) -> AgentOutput:
        cls = self.classifier.classify(message)
        precedents = self.retriever.search(message, k=k)
        call = decide(message, cls["intent"], cls["confidence"])

        # A draft is produced even when escalating: a human agent gets a suggested reply
        # to edit, which is how these systems are actually used.
        reply = self.drafter.draft(message, cls["intent"], precedents)

        return AgentOutput(
            message=message,
            intent=cls["intent"],
            confidence=cls["confidence"],
            decision=call.decision,
            reason=call.reason,
            reply=reply,
            precedents=[
                {"message": p.customer_message, "reply": p.brand_reply,
                 "score": round(p.score, 3)}
                for p in precedents
            ],
        )
