"""Score the second annotator's filled sheet against the LLM judge, and against my own
blind pass if the two overlap — the first real inter-annotator check in this project.

Two prior solo attempts at judge-vs-human agreement were degenerate (I answered yes to
everything, both times), which is a property of one person rating twice, not evidence
about the judge. This is what actually answers the assignment's question, because the
second rater has no reason to converge on my answers or the judge's.
"""
import csv

import _bootstrap  # noqa: F401
from support_agent.config import resolve
from support_agent.eval.metrics import kappa

SENDABLE_YES = {"y", "yes", "1", "true", "sendable"}
SENDABLE_NO = {"n", "no", "0", "false"}


def parse_sendable(raw: str) -> bool | None:
    v = (raw or "").strip().lower()
    if v in SENDABLE_YES:
        return True
    if v in SENDABLE_NO:
        return False
    return None


def interpret(k: float | None, degenerate: bool) -> str:
    if degenerate:
        return ("UNDEFINED: one rater never varied, so kappa is not computable and this "
                "comparison carries no information")
    if k < 0.2:
        return "poor"
    if k < 0.4:
        return "fair"
    if k < 0.6:
        return "moderate"
    if k < 0.8:
        return "substantial"
    return "near-perfect"


def agreement(a: dict[str, bool], b: dict[str, bool]) -> dict:
    ids = [i for i in a if i in b]
    x = [int(a[i]) for i in ids]
    y = [int(b[i]) for i in ids]
    degenerate = len(set(x)) < 2 or len(set(y)) < 2
    k = None if degenerate else kappa(x, y)
    return {
        "n": len(ids),
        "raw_agreement": round(sum(p == q for p, q in zip(x, y)) / max(len(ids), 1), 3),
        "cohens_kappa": k,
        "degenerate": degenerate,
        "interpretation": interpret(k, degenerate),
    }


def main():
    sheet = resolve("data/golden/second_annotator_sheet.csv")
    with open(sheet, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    second: dict[str, bool] = {}
    problems = []
    for i, r in enumerate(rows, start=2):
        raw = r.get("sendable", "")
        if not (raw or "").strip():
            problems.append(f"  row {i} (thread {r.get('thread_id')}): not scored yet")
            continue
        val = parse_sendable(raw)
        if val is None:
            problems.append(f"  row {i} (thread {r.get('thread_id')}): "
                             f"unreadable sendable value {raw!r}")
            continue
        second[r["thread_id"]] = val

    if problems:
        print(f"{len(problems)} row(s) not usable yet:")
        print("\n".join(problems[:25]))
        if not second:
            raise SystemExit("Nothing scored. Fix the sheet and rerun.")
        print(f"Continuing with the {len(second)} rows that ARE scored.\n")

    import json

    judged = json.loads(resolve("reports/results.json").read_text())
    judge = {
        str(s["thread_id"]): bool(s.get("sendable"))
        for s in judged["systems"]["agent"]["reply_quality"]["per_example"]
    }
    result = {"second_vs_judge": agreement(second, judge)}

    first_pass_path = resolve("data/golden/human_judge_scores.csv")
    if first_pass_path.exists():
        with open(first_pass_path, newline="", encoding="utf-8") as fh:
            first = {r["thread_id"]: bool(int(r["human_sendable"]))
                     for r in csv.DictReader(fh)}
        result["second_vs_first_annotator"] = agreement(second, first)

    out = resolve("reports/second_annotator_agreement.json")
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
