"""The intent taxonomy — a human judgement, defined after reading real Delta threads.

Edit this file yourself after running scripts/explore_intents.py. Keep it small: a set
you cannot label consistently by hand is a set the model cannot learn or be scored on.
Each entry needs a definition precise enough that you would label the same message the
same way twice, a week apart. That is the real test.
"""
from __future__ import annotations

INTENTS: dict[str, str] = {
    "rebooking_change": (
        "Wants to change, rebook or cancel a flight, or is asking why a change was "
        "handled the way it was. Includes missed connections."
    ),
    "delay_cancellation": (
        "Reporting or asking about a delayed, cancelled or diverted flight, including "
        "the knock-on effects of one."
    ),
    "baggage": "Lost, delayed, damaged, or charged-for baggage.",
    "website_app_issue": (
        "The website, app, kiosk or check-in system is broken or behaving wrongly."
    ),
    "inflight_experience": (
        "Something about the onboard experience: seat, crew, wifi/entertainment, food, "
        "cleanliness."
    ),
    "loyalty_refund_compensation": (
        "SkyMiles/Medallion status, refunds, vouchers, or a request for compensation."
    ),
    "praise": "Positive feedback with no issue to resolve.",
    "other": (
        "Real message that fits none of the above, including pure venting with no "
        "actionable request. Use sparingly — if this exceeds ~10% the taxonomy is wrong."
    ),
}

# Tie-break rules, written BEFORE labelling started and applied to all 200 examples.
# Without these, the same message gets labelled differently on Monday and Wednesday, and
# every "accuracy" number downstream is measuring the labeller's mood.
TIE_BREAKS = (
    "Label by what the customer is ASKING FOR, not by what happened to them. "
    "'Delayed, missed my connection, can you rebook me' -> rebooking_change. "
    "'Delayed 7 hours, where is the plane you promised' -> delay_cancellation.",
    "If the message asks for money or miles back, it is loyalty_refund_compensation, "
    "even when a bag or a delay caused it.",
    "A message that mentions a bag ONLY as context for a delay is delay_cancellation; "
    "baggage means the bag itself is the problem.",
    "Praise plus a small complaint -> the complaint wins; praise is for messages with "
    "nothing to resolve.",
    "Sarcasm with no request ('great job as always') -> other, not praise.",
)

# Decisions the agent must make about handling.
DECISIONS = ("auto", "escalate")

INTENT_NAMES = tuple(INTENTS)
