"""Export a blind scoring sheet for a SECOND, independent person.

Two of my own attempts at judge-vs-human agreement both came back degenerate: I marked
every reply sendable, twice, so Cohen's kappa was undefined both times (see DECISIONS.md).
That is a property of asking the same person twice, not of the judge. A genuinely
independent second rater is the fix.

The sheet contains only the customer message and the agent's draft reply — no intent, no
judge verdict, no hint of what "sendable" should mean beyond the guide. Rows are shuffled
(deterministically, off the project's random seed) so the sheet isn't obviously in the
same order as my own pass, which the annotator should never see.
"""
import csv
import json
import random

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve

FIELDS = ["thread_id", "customer_message", "agent_reply", "sendable", "note"]

GUIDE = """# Scoring these replies (10-15 minutes)

You're looking at real customer messages sent to Delta Air Lines on Twitter, and a
reply an AI support agent drafted for each one. For every row, ask yourself one
question:

    Would I send THIS reply, unedited, to THIS customer, as Delta?

Answer in the `sendable` column: `y` (yes) or `n` (no). Say no when the reply:
- deflects a customer who is angry, stranded, or describing something serious into a
  generic "DM us your confirmation number"
- answers a different question than the one asked
- promises something Delta may not actually do (a refund, compensation, a specific fix)
- doesn't match how upset or urgent the customer sounds

Use the `note` column for anything you noticed, even a couple of words - optional.

Please don't discuss individual answers with anyone else scoring this, and don't look
up the messages or replies online. There's no answer key: your honest read is the data.

When you're done, save the file (keep it a CSV) and send it back.
"""


def main():
    cfg = load_config()
    preds = json.loads(resolve("reports/predictions.json").read_text())["agent"]
    judged = json.loads(resolve("reports/results.json").read_text())
    judge_rows = {
        str(s["thread_id"])
        for s in judged["systems"]["agent"]["reply_quality"]["per_example"]
    }
    n_target = cfg["eval"]["judge_sample_for_human_agreement"]
    pool = [p for p in preds if str(p["thread_id"]) in judge_rows][:n_target]

    # Shuffle so the sheet doesn't mirror my own scoring pass's order, without touching
    # the underlying random module state anything else in the run might depend on.
    rng = random.Random(cfg["random_seed"])
    shuffled = pool[:]
    rng.shuffle(shuffled)

    out = resolve("data/golden/second_annotator_sheet.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for p in shuffled:
            w.writerow([p["thread_id"], p["message"], p["reply"], "", ""])

    resolve("data/golden/SECOND_ANNOTATOR_GUIDE.md").write_text(GUIDE)
    print(f"Wrote {len(shuffled)} rows -> {out}")
    print("Guide -> data/golden/SECOND_ANNOTATOR_GUIDE.md")
    print("Send both files to your annotator; they need no dev environment, just a "
          "spreadsheet app.")


if __name__ == "__main__":
    main()
