"""Export the frozen pool as a spreadsheet to hand-label, for people who label faster in
a grid than in a terminal prompt.

Same labels, same pool, same ground truth — only the input method differs. The sheet
deliberately does NOT contain any model prediction: seeing one would anchor the labeller
and quietly inflate every agreement number computed later.
"""
import csv
import json

import _bootstrap  # noqa: F401
from support_agent.config import resolve
from support_agent.intents import INTENTS, INTENT_NAMES, TIE_BREAKS

if __name__ == "__main__":
    with open(resolve("data/golden/pool.jsonl"), encoding="utf-8") as fh:
        pool = [json.loads(line) for line in fh if line.strip()]

    out = resolve("data/golden/to_label.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["thread_id", "customer_message", "delta_actual_reply",
                    "intent", "decision", "note"])
        for t in pool:
            w.writerow([t["thread_id"], t["customer_message"],
                        t.get("brand_reply") or "", "", "", ""])

    guide = resolve("data/golden/LABELLING_GUIDE.md")
    lines = ["# How to fill in to_label.csv", "",
             "Fill the `intent` column with one of these names (or its number):", ""]
    for i, (name, desc) in enumerate(INTENTS.items()):
        lines.append(f"- `{i}` **{name}** — {desc}")
    lines += ["", "Fill `decision` with `auto` or `escalate` (or just `a` / `e`).", "",
              "Escalate when answering needs their booking or account details, when "
              "money or compensation is at stake, when they are stranded right now, or "
              "when the tone is angry enough that a canned reply makes it worse. "
              "Everything else is auto.", "",
              "Use `note` whenever you hesitated. Those notes become the failure "
              "analysis.", "", "## Tie-break rules", ""]
    lines += [f"- {r}" for r in TIE_BREAKS]
    lines += ["", "When done, save as CSV (same filename) and run:", "",
              "```", ".venv/bin/python scripts/import_labelling_sheet.py", "```"]
    guide.write_text("\n".join(lines))

    print(f"Wrote {len(pool)} rows -> {out}")
    print(f"Instructions -> {guide}")
