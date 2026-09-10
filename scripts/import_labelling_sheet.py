"""Import the hand-filled spreadsheet into the golden set, validating every row.

Validation is strict on purpose: a typo'd intent silently becoming its own class would
corrupt every metric downstream, and the failure would look like a modelling problem
rather than a data-entry one.
"""
import csv

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.intents import INTENT_NAMES

FIELDS = ["thread_id", "customer_message", "brand_reply", "intent", "decision", "note"]
DECISION_ALIASES = {"a": "auto", "auto": "auto", "e": "escalate", "esc": "escalate",
                    "escalate": "escalate"}


def normalise_intent(raw: str) -> str | None:
    raw = (raw or "").strip().lower()
    if not raw:
        return None
    if raw.isdigit() and int(raw) < len(INTENT_NAMES):
        return INTENT_NAMES[int(raw)]
    return raw if raw in INTENT_NAMES else None


if __name__ == "__main__":
    cfg = load_config()
    src = resolve("data/golden/to_label.csv")
    with open(src, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    good, problems = [], []
    for i, r in enumerate(rows, start=2):  # +2: header row and 1-indexing, as in a sheet
        intent = normalise_intent(r.get("intent", ""))
        decision = DECISION_ALIASES.get((r.get("decision") or "").strip().lower())
        if intent is None and decision is None and not (r.get("note") or "").strip():
            continue  # untouched row, simply not labelled yet
        if intent is None:
            problems.append(f"  row {i}: bad intent {r.get('intent')!r}")
            continue
        if decision is None:
            problems.append(f"  row {i}: bad decision {r.get('decision')!r}")
            continue
        good.append({
            "thread_id": r["thread_id"],
            "customer_message": r["customer_message"],
            "brand_reply": r.get("delta_actual_reply", ""),
            "intent": intent,
            "decision": decision,
            "note": (r.get("note") or "").strip(),
        })

    if problems:
        print(f"{len(problems)} row(s) need fixing before import:")
        print("\n".join(problems[:25]))
        raise SystemExit("Nothing written. Fix those rows and rerun.")

    out = resolve(cfg["eval"]["golden_path"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(good)

    from collections import Counter
    print(f"Imported {len(good)} labelled rows -> {out}")
    print("Intents:", dict(Counter(g['intent'] for g in good)))
    print("Decisions:", dict(Counter(g['decision'] for g in good)))
    print("Notes written:", sum(1 for g in good if g["note"]))
