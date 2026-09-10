"""Intent classification with a few-shot LLM prompt.

Temperature 0 and a closed label set. If the model returns something outside the set we
record it as `unparseable` rather than silently mapping it to `other` — an off-menu
answer is a different failure from a wrong answer, and the report distinguishes them.
"""
from __future__ import annotations

import json

from ..intents import INTENTS, INTENT_NAMES
from ..llm import LLM

PROMPT = """You are classifying inbound customer messages sent to Delta Air Lines on Twitter.

Choose exactly ONE intent from this list:
{taxonomy}

Rules:
- Choose the intent matching the customer's PRIMARY request, not every topic mentioned.
- If the message only vents with no actionable request, choose "other".
- Answer with JSON only: {{"intent": "<name>", "confidence": <0.0-1.0>}}

Customer message:
\"\"\"{message}\"\"\"
"""


class IntentClassifier:
    def __init__(self, llm: LLM | None = None, cfg: dict | None = None):
        self.llm = llm or LLM(cfg)
        self.cfg = (cfg or {}).get("llm", {})
        self.taxonomy = "\n".join(f"- {n}: {d}" for n, d in INTENTS.items())

    def classify(self, message: str) -> dict:
        prompt = PROMPT.format(taxonomy=self.taxonomy, message=message)
        try:
            out = self.llm.complete_json(
                prompt,
                temperature=self.cfg.get("temperature_classify", 0.0),
                max_tokens=self.cfg.get("max_tokens_classify", 150),
            )
        except (json.JSONDecodeError, ValueError):
            # The model answered, but not with parseable JSON. That is a genuine model
            # failure and belongs in the metrics as `unparseable`.
            return {"intent": "unparseable", "confidence": 0.0}
        # NOTE: transport errors (bad model name, exhausted quota, network) are
        # deliberately NOT caught. An earlier version swallowed them here, so a dead API
        # key produced 196 confident-looking "unparseable" rows and an intent accuracy of
        # zero with no error anywhere. A crash is the correct behaviour: it distinguishes
        # "the model was wrong" from "there was no model". See DECISIONS.md #11.
        intent = str(out.get("intent", "")).strip()
        if intent not in INTENT_NAMES:
            return {"intent": "unparseable", "confidence": 0.0}
        try:
            conf = float(out.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        return {"intent": intent, "confidence": max(0.0, min(1.0, conf))}
