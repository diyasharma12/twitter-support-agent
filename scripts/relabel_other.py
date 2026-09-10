"""Second labelling pass over ONLY the rows first labelled `other`.

Why this script exists: on the first pass 42% of the golden set landed in `other`, not
because the labelling was careless but because the taxonomy had no bucket for policy
questions, ground-service complaints or plain chit-chat. Those three categories were
added afterwards, and this pass re-files the affected rows against the revised set.

Only rows previously marked `other` are shown, and the auto/escalate decision made on
the first pass is preserved untouched — re-opening decisions that were made against the
same evidence would be churn, not correction.
"""
import csv
import textwrap

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.intents import INTENTS, INTENT_NAMES

FIELDS = ["thread_id", "customer_message", "brand_reply", "intent", "decision", "note"]
NEW = ("general_question", "service_complaint", "social_chitchat")


def main():
    cfg = load_config()
    path = resolve(cfg["eval"]["golden_path"])
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    targets = [r for r in rows if r["intent"] == "other"]
    print(f"\n{len(targets)} rows to re-file. The new buckets are:")
    for n in NEW:
        print(f"  {n}: {INTENTS[n]}")
    print("\nKeep 'other' only if it truly fits nowhere. Ctrl-C saves and stops.\n")

    menu = "  ".join(f"[{i}] {n}" for i, n in enumerate(INTENT_NAMES))
    changed = 0
    try:
        for i, r in enumerate(targets, 1):
            print("=" * 78)
            print(f"[{i}/{len(targets)}]  (decision stays '{r['decision']}')")
            print(textwrap.fill(r["customer_message"], 76, initial_indent="  ",
                                subsequent_indent="  "))
            print(f"\n{menu}   [?] definitions")
            while True:
                raw = input("intent > ").strip().lower()
                if raw == "?":
                    for name, desc in INTENTS.items():
                        print(f"  {name}: {desc}")
                    continue
                if raw.isdigit() and int(raw) < len(INTENT_NAMES):
                    new = INTENT_NAMES[int(raw)]
                elif raw in INTENT_NAMES:
                    new = raw
                else:
                    print("  ?")
                    continue
                break
            if new != r["intent"]:
                r["intent"] = new
                changed += 1
            print()
    except KeyboardInterrupt:
        print("\nStopping — writing what you have.")

    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print(f"\nRe-filed {changed} rows. New distribution:")
    for k, v in Counter(r["intent"] for r in rows).most_common():
        print(f"  {k:<32}{v:>4}  {v/len(rows):>6.1%}")


if __name__ == "__main__":
    main()
