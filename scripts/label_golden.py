"""Terminal labelling tool for the golden set. Resumable — quit any time with 'q'.

You label three things per example:
  intent    — which bucket from src/support_agent/intents.py
  decision  — should an AI agent handle this alone (auto) or hand it to a human (escalate)
  note      — optional, but write one whenever the example was hard. Those notes become
              the failure analysis and the "what counts as good" section of the report.

Deliberately NOT shown to you while labelling: nothing from the model. These labels are
the ground truth; seeing a prediction first would anchor you and quietly inflate every
agreement number you later report.
"""
import csv
import json
import sys
import textwrap

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.intents import INTENTS, INTENT_NAMES, TIE_BREAKS

FIELDS = ["thread_id", "customer_message", "brand_reply", "intent", "decision", "note"]


def load_done(path):
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {row["thread_id"]: row for row in csv.DictReader(fh)}


def main():
    cfg = load_config()
    pool_path = resolve("data/golden/pool.jsonl")
    out_path = resolve(cfg["eval"]["golden_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(pool_path, encoding="utf-8") as fh:
        pool = [json.loads(line) for line in fh if line.strip()]

    done = load_done(out_path)
    todo = [t for t in pool if str(t["thread_id"]) not in done]

    print(f"\n{len(done)} labelled, {len(todo)} to go.\n")
    menu = "  ".join(f"[{i}] {n}" for i, n in enumerate(INTENT_NAMES))

    new_file = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()

        for i, t in enumerate(todo, 1):
            print("=" * 78)
            print(f"[{i}/{len(todo)}]  thread {t['thread_id']}")
            print("=" * 78)
            print("CUSTOMER:")
            print(textwrap.fill(t["customer_message"], 76, initial_indent="  ",
                                subsequent_indent="  "))
            print("\nWHAT DELTA ACTUALLY REPLIED:")
            print(textwrap.fill(t.get("brand_reply") or "(none)", 76,
                                initial_indent="  ", subsequent_indent="  "))
            print(f"\n{menu}   [?] definitions   [q] quit")

            intent = None
            while intent is None:
                raw = input("intent > ").strip().lower()
                if raw == "q":
                    print(f"\nStopped. {len(done) + i - 1} labelled so far.")
                    return
                if raw == "?":
                    for name, desc in INTENTS.items():
                        print(f"  {name}: {desc}")
                    print("\n  TIE-BREAK RULES:")
                    for rule in TIE_BREAKS:
                        print(f"   - {rule}")
                    continue
                if raw.isdigit() and int(raw) < len(INTENT_NAMES):
                    intent = INTENT_NAMES[int(raw)]
                elif raw in INTENT_NAMES:
                    intent = raw
                else:
                    print("  ?")

            decision = None
            while decision is None:
                raw = input("auto [a] or escalate [e] > ").strip().lower()
                if raw in ("a", "auto"):
                    decision = "auto"
                elif raw in ("e", "esc", "escalate"):
                    decision = "escalate"
                elif raw == "q":
                    return
                else:
                    print("  a or e")

            note = input("note (enter to skip) > ").strip()

            writer.writerow({
                "thread_id": t["thread_id"],
                "customer_message": t["customer_message"],
                "brand_reply": t.get("brand_reply") or "",
                "intent": intent,
                "decision": decision,
                "note": note,
            })
            fh.flush()
            print()

    print("\nPool complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped — progress is saved.")
        sys.exit(0)
