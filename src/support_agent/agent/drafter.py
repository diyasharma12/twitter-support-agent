"""Draft a reply grounded in retrieved precedent.

The prompt gives the model real historical (message -> reply) pairs from this brand and
tells it to imitate the brand's handling, not to invent policy. It is explicitly told it
may not promise anything the precedents do not support — hallucinated promises
("we've refunded you") are the failure mode that would actually hurt a support team.
"""
from __future__ import annotations

from ..llm import LLM
from .retriever import Precedent

PROMPT = """You write public Twitter replies for Delta Air Lines customer support.

How this brand has handled similar messages before:
{precedents}

Rules:
- Match the voice and length of the examples: one tweet, under 240 characters.
- Only offer what the examples show this brand actually does. Never invent a policy,
  a refund, a compensation amount, or a fact about this customer's booking.
- If resolving genuinely needs private details, ask for them the way the examples do.
- No hashtags. Do not sign off with an agent's initials.

New customer message (intent: {intent}):
\"\"\"{message}\"\"\"

Reply with the tweet text only, nothing else."""


def format_precedents(precedents: list[Precedent]) -> str:
    if not precedents:
        return "(no close precedent found)"
    return "\n\n".join(
        f"Customer: {p.customer_message}\nDelta: {p.brand_reply}" for p in precedents
    )


class ReplyDrafter:
    def __init__(self, llm: LLM | None = None, cfg: dict | None = None):
        self.llm = llm or LLM(cfg)
        self.cfg = (cfg or {}).get("llm", {})

    def draft(self, message: str, intent: str, precedents: list[Precedent]) -> str:
        prompt = PROMPT.format(
            precedents=format_precedents(precedents), intent=intent, message=message
        )
        text = self.llm.complete(
            prompt, temperature=self.cfg.get("temperature_draft", 0.3)
        )
        return text.strip().strip('"')
