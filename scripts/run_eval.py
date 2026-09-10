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

JUDGE_LIMIT = 40  # judged replies per system; the free tier caps tokens per DAY


def load_golden(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("intent")]
    if not rows:
        raise SystemExit(f"No labelled rows in {path}. Run scripts/label_golden.py first.")
    return rows


def cross_val_predict_simple(rows, retriever):
    """Out-of-fold predictions for the simple baseline.

    The baseline is the only system that learns from the golden labels, so it must never
    be scored on a row it was fitted to. An earlier version stratified the folds and fell
    back to fit-on-everything when any class had fewer than two examples — which is
    exactly this dataset, since `loyalty_refund_compensation` has one. The fallback
    silently produced 1.000 accuracy by memorisation. Plain K-fold has no such
    requirement: a rare class may be absent from a training fold, the model simply never
    predicts it there, and that is an honest reflection of learning from 196 labels.
    See DECISIONS.md #14.
    """
    from sklearn.model_selection import KFold

    msgs = [r["customer_message"] for r in rows]
    intents = [r["intent"] for r in rows]
    preds = [None] * len(rows)

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    for train_idx, test_idx in kf.split(msgs):
        model = SimpleBaseline(retriever).fit(
            [msgs[i] for i in train_idx], [intents[i] for i in train_idx]
        )
        for i in test_idx:
            preds[i] = model.handle(msgs[i])

    assert all(p is not None for p in preds), "every row must get an out-of-fold prediction"
    return preds


def judge_replies(judge, rows, outputs, retriever, limit=JUDGE_LIMIT):
    scored = []
    for row, out in list(zip(rows, outputs))[:limit]:
        hits = retriever.search(row["customer_message"], k=2)
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


def preflight(llm, cfg):
    """One live call before the real run.

    Without this, a wrong model name or an exhausted quota is discovered several minutes
    and several hundred cached-miss calls into the run.
    """
    try:
        llm.complete("Reply with the single word: ok", temperature=0.0, use_cache=False)
    except Exception as err:  # noqa: BLE001 - we want the raw provider message here
        raise SystemExit(
            f"\nLLM preflight failed, so the run was not started:\n  {err}\n\n"
            f"Model in config.yaml: {cfg['llm']['model']}\n"
            "If the provider says the model is retired, put the name it suggests into "
            "config.yaml under llm.model and rerun."
        )
    print(f"preflight ok ({cfg['llm']['model']})")


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
    preflight(llm, cfg)
    agent = SupportAgent(retriever, cfg, llm)
    agent_out = []
    for i, m in enumerate(msgs, 1):
        agent_out.append(agent.handle(m).to_dict())
        if i % 20 == 0:
            print(f"  agent {i}/{len(msgs)}")
    systems["agent"] = agent_out
    print("agent done")

    judge = ReplyJudge(cfg=cfg)  # its own model, its own token budget
    print(f"judge model: {judge.model_name}")
    results = {"golden_n": len(rows), "brand": cfg["brand"], "systems": {}}
    out_path = resolve("reports/results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for name, outs in systems.items():
        results["systems"][name] = {
            "intent": intent_metrics(true_intent, [o["intent"] for o in outs]),
            "escalation": escalation_metrics(
                true_decision, [o["decision"] for o in outs]
            ),
            "reply_quality": judge_replies(judge, rows, outs, retriever),
        }
        # Written after every system, so a quota failure part-way through leaves usable
        # results instead of nothing. Learned the hard way.
        out_path.write_text(json.dumps(results, indent=2))
        print(f"judged {name}")

    results["runtime_seconds"] = round(time.time() - t0, 1)
    results["judge_model"] = judge.model_name
    results["model"] = cfg["llm"]["model"]
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
