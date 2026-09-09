"""Auto-handle vs escalate, as explicit rules over signals rather than an LLM vibe check.

Why rules: an escalation policy is a business decision a support lead must be able to
read, argue with and change. A rule that fires on a named signal can be audited; a
model's opinion cannot. The LLM contributes signals (intent, confidence), the policy
decides — and every decision carries the rule that produced it.

The asymmetry is deliberate. A wrongly auto-handled angry stranded customer costs far
more than a needlessly escalated easy one, so ties escalate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Intents where a public tweet can rarely resolve the issue on its own.
ALWAYS_ESCALATE_INTENTS = {"loyalty_refund_compensation", "baggage"}

# Signals that the agent cannot act on without private account data.
ACCOUNT_DATA_RE = re.compile(
    r"\b(confirmation number|booking ref|record locator|skymiles|my account|"
    r"credit card|refund me|charged|ticket number)\b",
    re.I,
)
# Signals of a customer who is stuck right now, where a wrong reply is expensive.
STRANDED_RE = re.compile(
    r"\b(stranded|stuck at|missed my connection|missed connection|no one is helping|"
    r"still waiting|been on hold|tarmac|about to miss)\b",
    re.I,
)
# Severe / legal / safety language.
SEVERE_RE = re.compile(
    r"\b(lawyer|legal action|sue|discriminat|assault|racist|unsafe|emergency|"
    r"medical|wheelchair|disabled|complaint to the dot)\b",
    re.I,
)

CONFIDENCE_FLOOR = 0.6


@dataclass
class Decision:
    decision: str  # "auto" | "escalate"
    reason: str


def decide(message: str, intent: str, confidence: float) -> Decision:
    """Return the handling decision and the single rule that produced it."""
    if SEVERE_RE.search(message):
        return Decision("escalate", "severe/legal/safety language needs a human")
    if STRANDED_RE.search(message):
        return Decision("escalate", "customer appears stranded or mid-disruption")
    if ACCOUNT_DATA_RE.search(message):
        return Decision("escalate", "resolution requires private account data")
    if intent in ALWAYS_ESCALATE_INTENTS:
        return Decision("escalate", f"intent '{intent}' is rarely resolvable in public")
    if intent == "unparseable" or confidence < CONFIDENCE_FLOOR:
        return Decision("escalate", f"low intent confidence ({confidence:.2f})")
    return Decision("auto", f"routine '{intent}' with confidence {confidence:.2f}")
