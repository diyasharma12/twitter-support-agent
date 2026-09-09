"""Metric maths gets a test with a hand-computed answer, because a quietly wrong metric
is the worst possible bug in a project whose whole point is measurement."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from support_agent.eval.metrics import escalation_metrics, intent_metrics


def test_escalation_counts_missed_escalations():
    true = ["escalate", "escalate", "auto", "auto"]
    pred = ["escalate", "auto", "auto", "escalate"]
    m = escalation_metrics(true, pred)
    assert m["missed_escalations"] == 1
    assert m["needless_escalations"] == 1
    assert m["recall_escalate"] == 0.5
    assert m["precision_escalate"] == 0.5


def test_intent_metrics_flag_unparseable():
    m = intent_metrics(["baggage", "baggage"], ["baggage", "unparseable"])
    assert m["accuracy"] == 0.5
    assert m["unparseable_rate"] == 0.5
