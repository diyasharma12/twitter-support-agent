"""Guard against the leak that produced a fake 1.000.

The simple baseline learns from the golden labels, so its reported score must come from
out-of-fold predictions. A perfect score on this data is not a triumph, it is a symptom.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from support_agent.agent.retriever import Retriever
from support_agent.eval.metrics import intent_metrics


def _rows():
    """20 rows over 3 classes, one of which has a single member — the case that broke it."""
    out = []
    for i in range(9):
        out.append({"thread_id": i, "customer_message": f"my bag is lost at gate {i}",
                    "intent": "baggage", "decision": "escalate"})
    for i in range(10):
        out.append({"thread_id": 100 + i, "customer_message": f"thanks for the great flight {i}",
                    "intent": "praise", "decision": "auto"})
    out.append({"thread_id": 200, "customer_message": "refund my skymiles please",
                "intent": "loyalty_refund_compensation", "decision": "escalate"})
    return out


def test_simple_baseline_is_scored_out_of_fold():
    import run_eval

    rows = _rows()
    corpus = [{"thread_id": r["thread_id"], "customer_message": r["customer_message"],
               "brand_reply": "we can help"} for r in rows]
    preds = run_eval.cross_val_predict_simple(rows, Retriever(corpus))

    assert len(preds) == len(rows)
    m = intent_metrics([r["intent"] for r in rows], [p["intent"] for p in preds])
    # The singleton class cannot be learned out-of-fold, so a perfect score would mean
    # the model saw the row it was tested on.
    assert m["accuracy"] < 1.0, "perfect accuracy here means train-on-test leakage"
