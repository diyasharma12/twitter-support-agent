"""Produce the headline numbers. Must finish in under 15 minutes on the committed data.

Reads the hand-labelled golden set, runs the trivial baseline, the simple baseline and
the agent over it, scores intent + escalation with sklearn metrics and reply quality
with the LLM judge, and writes everything to reports/.

Nothing here prints a number that is not also written to reports/results.json, so the
README can never drift from what the code actually produced.
"""
import csv
import json
import time

import _bootstrap  # noqa: F401
from support_agent.agent.drafter import format_precedents
from support_agent.agent.pipeline import SupportAgent
from support_agent.agent.retriever import Retriever
from support_agent.config import load_config, resolve
from support_agent.eval.baselines import SimpleBaseline, TrivialBaseline
from support_agent.eval.judge import ReplyJudge
from support_agent.eval.metrics import escalation_metrics, intent_metrics
from support_agent.llm import LLM

JUDGE_LIMIT = 60  # judged replies per system, to stay inside the free-tier quota


def load_golden(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("intent")]
    if not rows:
        raise SystemExit(f"No labelled rows in {path}. Run scripts/label_golden.py first.")
    return rows


def cross_val_predict_simple(rows, retriever):
    """The simple baseline must not be trained on the rows it is scored on.

    With only ~200 labelled examples we cannot afford a held-out split AND a meaningful
    test set, so the simple baseline is evaluated with 5-fold cross-validation over the
    golden set. The agent and trivial baseline see no labels at all, so they are not
    advantaged by this — worth stating plainly in the report.
    """
    from sklearn.model_selection import StratifiedKFold
    import numpy as np

    msgs = [r["customer_message"] for r in rows]
    intents = [r["intent"] for r in rows]
    preds = [None] * len(rows)
    counts = {i: intents.count(i) for i in set(intents)}
    if min(counts.values()) < 2 or len(counts) < 2:
        model = SimpleBaseline(retriever).fit(msgs, intents)
        return [model.handle(m) for m in msgs]
    n_splits = min(5, min(counts.values()))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    for train_idx, test_idx in skf.split(np.zeros(len(msgs)), intents):
        model = SimpleBaseline(retriever).fit(
            [msgs[i] for i in train_idx], [intents[i] for i in train_idx]
        )
        for i in test_idx:
            preds[i] = model.handle(msgs[i])
    return preds


def judge_replies(judge, rows, outputs, retriever, limit=JUDGE_LIMIT):
    scored = []
    for row, out in list(zip(rows, outputs))[:limit]:
        hits = retriever.search(row["customer_message"], k=3)
        s = judge.score(row["customer_message"], out["reply"], format_precedents(hits))
        scored.append({"thread_id": row["thread_id"], **s})
    def avg(key):
        vals = [s[key] for s in scored if isinstance(s.get(key), int)]
        return round(sum(vals) / len(vals), 3) if vals else None
    return {
        "n_judged": len(scored),
        "grounded": avg("grounded"),
        "tone": avg("tone"),
        "resolution": avg("resolution"),
        "sendable_rate": round(
            sum(1 for s in scored if s.get("sendable")) / max(len(scored), 1), 3
        ),
        "per_example": scored,
    }


def main():
    t0 = time.time()
    cfg = load_config()
    rows = load_golden(resolve(cfg["eval"]["golden_path"]))
    golden_ids = {str(r["thread_id"]) for r in rows}
    print(f"Golden set: {len(rows)} labelled examples")

    retriever = Retriever.from_sample(
        resolve(cfg["data"]["sample_jsonl"], brand=cfg["brand"]), exclude_ids=golden_ids
    )
    print(f"Retrieval corpus: {len(retriever.corpus)} threads (golden ids excluded)")

    msgs = [r["customer_message"] for r in rows]
    true_intent = [r["intent"] for r in rows]
    true_decision = [r["decision"] for r in rows]

    systems = {}

    trivial = TrivialBaseline().fit(msgs, true_intent)
    systems["trivial"] = [trivial.handle(m) for m in msgs]
    print("trivial baseline done")

    systems["simple"] = cross_val_predict_simple(rows, retriever)
    print("simple baseline done")

    llm = LLM(cfg)
    agent = SupportAgent(retriever, cfg, llm)
    agent_out = []
    for i, m in enumerate(msgs, 1):
        agent_out.append(agent.handle(m).to_dict())
        if i % 20 == 0:
            print(f"  agent {i}/{len(msgs)}")
    systems["agent"] = agent_out
    print("agent done")

    judge = ReplyJudge(llm, cfg)
    results = {"golden_n": len(rows), "brand": cfg["brand"], "systems": {}}
    for name, outs in systems.items():
        results["systems"][name] = {
            "intent": intent_metrics(true_intent, [o["intent"] for o in outs]),
            "escalation": escalation_metrics(
                true_decision, [o["decision"] for o in outs]
            ),
            "reply_quality": judge_replies(judge, rows, outs, retriever),
        }
        print(f"judged {name}")

    results["runtime_seconds"] = round(time.time() - t0, 1)
    out_path = resolve("reports/results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))

    with open(resolve("reports/predictions.json"), "w") as fh:
        json.dump(
            {n: [{"thread_id": r["thread_id"], **o} for r, o in zip(rows, outs)]
             for n, outs in systems.items()}, fh, indent=2)

    print("\n" + "=" * 74)
    hdr = f"{'system':<10}{'intent acc':>12}{'macro F1':>11}{'esc recall':>12}{'sendable':>11}"
    print(hdr); print("-" * len(hdr))
    for name, r in results["systems"].items():
        print(f"{name:<10}{r['intent']['accuracy']:>12.3f}{r['intent']['macro_f1']:>11.3f}"
              f"{r['escalation']['recall_escalate']:>12.3f}"
              f"{r['reply_quality']['sendable_rate']:>11.3f}")
    print("=" * 74)
    print(f"Wrote reports/results.json in {results['runtime_seconds']}s")


if __name__ == "__main__":
    main()
