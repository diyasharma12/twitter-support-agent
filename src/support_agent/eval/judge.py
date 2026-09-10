"""LLM-as-judge for reply quality, plus the machinery to check whether it can be trusted.

A judge is just another model, so its scores are a claim, not a measurement, until they
are shown to agree with a human. `scripts/judge_human_check.py` samples replies for the
author to score blind, and the agreement (Cohen's kappa on a binarised acceptable/not)
is reported next to every judged number.

The rubric scores three things separately because they fail separately: a reply can be
perfectly on-brand and still invent a refund.
"""
from __future__ import annotations

import json

from ..llm import LLM

RUBRIC = """You are evaluating a draft public reply written by an AI support agent for
Delta Air Lines on Twitter.

Customer message:
\"\"\"{message}\"\"\"

How Delta has actually handled similar messages:
{precedents}

Draft reply to evaluate:
\"\"\"{reply}\"\"\"

Score each dimension 1-5 (5 is best):
- grounded: does it only offer what this brand plausibly does, per the precedents?
  Score 1 if it invents a policy, a refund, a compensation amount, or a fact about this
  customer's booking.
- tone: appropriate empathy and register for the customer's emotional state.
- resolution: does it move the issue forward — a real next step, not empty apology?

Also answer: would a human support lead send this as-is, yes or no?

Answer with JSON only:
{{"grounded": <1-5>, "tone": <1-5>, "resolution": <1-5>, "sendable": <true|false>,
  "why": "<one short sentence>"}}"""


class ReplyJudge:
    """Scores reply quality with a model deliberately different from the drafter's.

    Judging with the same model that wrote the reply invites self-preference bias — a
    model tends to rate its own family's output generously. Using another family does not
    remove judge bias, it only removes that particular one; the human agreement check is
    still what bounds how far these scores can be trusted.
    """

    def __init__(self, llm: LLM | None = None, cfg: dict | None = None):
        cfg = cfg or {}
        llm_cfg = cfg.get("llm", {})
        judge_model = llm_cfg.get("judge_model")
        self.llm = llm or LLM(cfg or None, model=judge_model)
        self.model_name = self.llm.model
        self.cfg = llm_cfg

    def score(self, message: str, reply: str, precedents_text: str) -> dict:
        prompt = RUBRIC.format(
            message=message, reply=reply, precedents=precedents_text or "(none)"
        )
        try:
            out = self.llm.complete_json(
                prompt, temperature=self.cfg.get("temperature_judge", 0.0)
            )
        except (json.JSONDecodeError, ValueError):
            return {"grounded": None, "tone": None, "resolution": None,
                    "sendable": None, "why": "judge output unparseable"}
        for key in ("grounded", "tone", "resolution"):
            try:
                out[key] = int(out.get(key))
            except (TypeError, ValueError):
                out[key] = None
        out["sendable"] = bool(out.get("sendable"))
        return out
