"""Regenerate reports/tables.md from results.json.

The report quotes numbers; this is where they come from. Nothing in the README is typed
by hand, so the write-up cannot drift from what the code actually produced.
"""
import json

import _bootstrap  # noqa: F401
from support_agent.config import resolve

WILSON_Z = 1.96


def ci95(p: float, n: int) -> float:
    """Half-width of a normal-approximation 95% interval, for honest error bars."""
    return WILSON_Z * ((p * (1 - p) / n) ** 0.5)


if __name__ == "__main__":
    res = json.loads(resolve("reports/results.json").read_text())
    n = res["golden_n"]
    lines = [f"# Generated results — {res['brand']}, n={n}", "",
             f"Agent model: `{res.get('model')}` · Judge model: `{res.get('judge_model')}`",
             f" · runtime {res.get('runtime_seconds')}s", "",
             "## Headline", "",
             "| system | intent acc | 95% CI | macro F1 | esc. recall | esc. precision | judged sendable |",
             "|---|---|---|---|---|---|---|"]
    for name, r in res["systems"].items():
        acc = r["intent"]["accuracy"]
        lines.append(
            f"| {name} | {acc:.3f} | ±{ci95(acc, n):.3f} | {r['intent']['macro_f1']:.3f} | "
            f"{r['escalation']['recall_escalate']:.3f} | "
            f"{r['escalation']['precision_escalate']:.3f} | "
            f"{r['reply_quality']['sendable_rate']:.3f} |"
        )

    lines += ["", "## Escalation confusion (positive class = escalate)", "",
              "| system | true pos | false pos | true neg | **missed escalations** | auto rate |",
              "|---|---|---|---|---|---|"]
    for name, r in res["systems"].items():
        c = r["escalation"]["counts"]
        lines.append(f"| {name} | {c['tp']} | {c['fp']} | {c['tn']} | **{c['fn']}** | "
                     f"{r['escalation']['auto_rate']:.3f} |")

    if any("escalation_v2" in r for r in res["systems"].values()):
        lines += ["", "## Escalation under labelling pass 2 (stated operating model)", "",
                  "| system | recall | precision | missed escalations | true escalations |",
                  "|---|---|---|---|---|"]
        for name, r in res["systems"].items():
            e = r.get("escalation_v2")
            if not e:
                continue
            lines.append(f"| {name} | {e['recall_escalate']:.3f} | "
                         f"{e['precision_escalate']:.3f} | {e['counts']['fn']} | "
                         f"{e['counts']['tp'] + e['counts']['fn']} |")

    lines += ["", "## Judge sub-scores (1–5)", "",
              "| system | n judged | grounded | tone | resolution | sendable |",
              "|---|---|---|---|---|---|"]
    for name, r in res["systems"].items():
        q = r["reply_quality"]
        lines.append(f"| {name} | {q['n_judged']} | {q['grounded']} | {q['tone']} | "
                     f"{q['resolution']} | {q['sendable_rate']:.3f} |")

    lines += ["", "## Agent per-class intent scores", "",
              "| intent | n in golden | precision | recall | f1 |", "|---|---|---|---|---|"]
    per = res["systems"]["agent"]["intent"]["per_class"]
    dist = res["systems"]["agent"]["intent"]["true_distribution"]
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        m = per.get(k)
        if not m:
            continue
        lines.append(f"| {k} | {v} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1-score']:.2f} |")

    out = resolve("reports/tables.md")
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
