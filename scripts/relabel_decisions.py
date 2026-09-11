"""Second pass over the auto/escalate labels, under an explicitly stated operating model.

Why this exists: the first pass labelled "could an AI resolve this with no human at all?"
while the policy decides "should a human take this over rather than the agent handling
it?". With the agent drafting a reply either way, those are different questions, and the
escalation metric was comparing them. `ESCALATION_MODEL` in intents.py states the model
this pass assumes; it was written before any re-labelling began.

Two safeguards, because this pass happens AFTER seeing where the agent fails:
  * ALL 196 rows are re-labelled, not just the ones the agent got wrong. Revisiting only
    the failures would improve the score by construction.
  * The agent's prediction is never shown, and rows are presented in a shuffled order so
    the session does not walk through the failures as a block.

The original labels are preserved as `decision_v1`, and the report gives results under
both.
"""
import csv
import random
import textwrap

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.intents import ESCALATION_MODEL

BAR = """
OPERATING MODEL: the agent drafts a reply for EVERY message, and a support agent sees it
before anything reaches the customer.

  [a] auto      the draft is an appropriate public reply; a human could send it after a
                glance. This INCLUDES "please DM us your confirmation number" — that is
                what Delta does publicly, and a human picks up the DM.

  [e] escalate  a human must take over WRITING the response, not just approve it:
                grief, fury, safety or legal issues, a stranded or time-critical
                customer, a compensation claim, or a case where a routine reply would
                make things materially worse.

  [q] quit      progress is saved.
"""


def main():
    cfg = load_config()
    path = resolve(cfg["eval"]["golden_path"])
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # Preserve the original pass under its own name, once.
    for r in rows:
        r.setdefault("decision_v1", r.get("decision", ""))
        if not r["decision_v1"]:
            r["decision_v1"] = r.get("decision", "")
        r.setdefault("decision_v2", "")

    fields = ["thread_id", "customer_message", "brand_reply", "intent",
              "decision", "decision_v1", "decision_v2", "note"]

    order = list(range(len(rows)))
    random.Random(cfg["random_seed"]).shuffle(order)
    todo = [i for i in order if not rows[i]["decision_v2"]]

    print(BAR)
    print(f"Model: {ESCALATION_MODEL}")
    print(f"{len(rows) - len(todo)} done, {len(todo)} to go. "
          "You will NOT see the agent's prediction.\n")

    def save():
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fields})

    try:
        for n, i in enumerate(todo, 1):
            r = rows[i]
            print("=" * 78)
            print(f"[{n}/{len(todo)}]  intent: {r['intent']}")
            print(textwrap.fill(r["customer_message"], 76,
                                initial_indent="  ", subsequent_indent="  "))
            while True:
                raw = input("\n[a] auto  [e] escalate  [?] rules  [q] quit > ").strip().lower()
                if raw == "q":
                    save()
                    print(f"\nSaved. {sum(1 for x in rows if x['decision_v2'])} re-labelled.")
                    return
                if raw == "?":
                    print(BAR)
                    continue
                if raw in ("a", "auto"):
                    r["decision_v2"] = "auto"
                elif raw in ("e", "esc", "escalate"):
                    r["decision_v2"] = "escalate"
                else:
                    print("  a or e")
                    continue
                break
            if n % 10 == 0:
                save()
            print()
    except KeyboardInterrupt:
        pass

    save()
    from collections import Counter
    v1 = Counter(r["decision_v1"] for r in rows)
    v2 = Counter(r["decision_v2"] for r in rows if r["decision_v2"])
    changed = sum(1 for r in rows if r["decision_v2"] and r["decision_v2"] != r["decision_v1"])
    print(f"\npass 1: {dict(v1)}")
    print(f"pass 2: {dict(v2)}")
    print(f"changed: {changed} of {sum(1 for r in rows if r['decision_v2'])}")


if __name__ == "__main__":
    main()
