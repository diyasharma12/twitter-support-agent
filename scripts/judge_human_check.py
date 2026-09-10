"""Measure whether the LLM judge agrees with a human — the assignment asks for evidence.

You score a sample of the agent's replies blind: you see the customer message and the
draft reply, but NOT the judge's verdict, so your answer cannot be anchored by it. Then
Cohen's kappa compares your yes/no against the judge's `sendable` flag.

Interpretation used in the report (Landis & Koch, and stated as a convention, not a law):
  < 0.20 poor, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, > 0.80 near-perfect.
A judge below 'moderate' means every judged number in this repo is decoration, and the
report must say so.
"""
import csv
import json
import sys
import textwrap

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.eval.metrics import kappa

FIELDS = ["thread_id", "human_sendable", "human_note"]


def main():
    cfg = load_config()
    preds = json.loads(resolve("reports/predictions.json").read_text())["agent"]
    judged = json.loads(resolve("reports/results.json").read_text())
    judge_rows = {
        str(s["thread_id"]): s
        for s in judged["systems"]["agent"]["reply_quality"]["per_example"]
    }
    n_target = cfg["eval"]["judge_sample_for_human_agreement"]
    pool = [p for p in preds if str(p["thread_id"]) in judge_rows][:n_target]

    out_path = resolve("data/golden/human_judge_scores.csv")
    done = {}
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {r["thread_id"]: r for r in csv.DictReader(fh)}

    todo = [p for p in pool if str(p["thread_id"]) not in done]
    print(f"\n{len(done)} scored, {len(todo)} to go. You will NOT see the judge's opinion.")
    print("""
The question is not 'is this reply reasonable?' — it is:
    Would I send THIS reply, unedited, to THIS customer, as Delta?

Say no when the reply deflects a customer who is angry, stranded or grieving into
'DM us your confirmation number'; when it answers a question the customer did not ask;
when it promises something Delta may not do; or when the tone does not match how upset
they are. A first pass that answers yes to everything produces no usable statistic —
kappa needs both raters to vary.
""")

    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for i, p in enumerate(todo, 1):
            print("=" * 78)
            print(f"[{i}/{len(todo)}] thread {p['thread_id']}")
            print("CUSTOMER:")
            print(textwrap.fill(p["message"], 76, initial_indent="  ",
                                subsequent_indent="  "))
            print("\nAGENT DRAFT:")
            print(textwrap.fill(p["reply"], 76, initial_indent="  ",
                                subsequent_indent="  "))
            ans = None
            while ans is None:
                raw = input("\nWould you send this as-is? [y/n/q] > ").strip().lower()
                if raw == "q":
                    print("Stopped — progress saved.")
                    return
                if raw in ("y", "n"):
                    ans = raw == "y"
            note = input("why (enter to skip) > ").strip()
            w.writerow({"thread_id": p["thread_id"], "human_sendable": int(ans),
                        "human_note": note})
            fh.flush()
            print()

    # Agreement
    with open(out_path, newline="", encoding="utf-8") as fh:
        human = {r["thread_id"]: int(r["human_sendable"]) for r in csv.DictReader(fh)}
    ids = [i for i in human if i in judge_rows]
    h = [human[i] for i in ids]
    j = [1 if judge_rows[i].get("sendable") else 0 for i in ids]
    agree = sum(a == b for a, b in zip(h, j)) / max(len(ids), 1)
    k = kappa(h, j)
    # Kappa corrects for chance agreement, which requires BOTH raters to vary. If one
    # rater gives the same answer every time, expected agreement equals observed
    # agreement and kappa collapses to 0.0 — which reads like "no agreement" but actually
    # means "this comparison carries no information". Say so rather than print the 0.
    degenerate = len(set(h)) < 2 or len(set(j)) < 2
    summary = {
        "n": len(ids),
        "raw_agreement": round(agree, 3),
        "cohens_kappa": None if degenerate else k,
        "human_sendable_rate": round(sum(h) / max(len(h), 1), 3),
        "judge_sendable_rate": round(sum(j) / max(len(j), 1), 3),
        "degenerate": degenerate,
        "interpretation": (
            "UNDEFINED: one rater never varied, so kappa is not computable and the judge "
            "remains unvalidated. Re-score with a stricter bar, or report the judge's "
            "numbers as unvalidated."
            if degenerate else
            "poor" if k < 0.2 else "fair" if k < 0.4 else "moderate" if k < 0.6
            else "substantial" if k < 0.8 else "near-perfect"
        ),
    }
    resolve("reports/judge_agreement.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nWrote reports/judge_agreement.json")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped — progress saved.")
        sys.exit(0)
