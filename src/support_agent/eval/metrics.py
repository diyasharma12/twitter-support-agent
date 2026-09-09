"""Metric maths, kept separate from the runner so it can be unit tested on tiny inputs.

Macro-F1 is reported alongside accuracy throughout, because this dataset is imbalanced
and accuracy alone would let a model that ignores every small intent look good.
"""
from __future__ import annotations

from collections import Counter

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def intent_metrics(true: list[str], pred: list[str]) -> dict:
    labels = sorted(set(true) | set(pred))
    return {
        "n": len(true),
        "accuracy": round(accuracy_score(true, pred), 4),
        "macro_f1": round(f1_score(true, pred, average="macro", zero_division=0), 4),
        "weighted_f1": round(
            f1_score(true, pred, average="weighted", zero_division=0), 4
        ),
        "unparseable_rate": round(
            sum(p == "unparseable" for p in pred) / max(len(pred), 1), 4
        ),
        "per_class": classification_report(
            true, pred, zero_division=0, output_dict=True
        ),
        "labels": labels,
        "confusion": confusion_matrix(true, pred, labels=labels).tolist(),
        "true_distribution": dict(Counter(true)),
    }


def escalation_metrics(true: list[str], pred: list[str]) -> dict:
    """'escalate' is the positive class: we care most about missed escalations."""
    yt = [1 if t == "escalate" else 0 for t in true]
    yp = [1 if p == "escalate" else 0 for p in pred]
    tp = sum(a and b for a, b in zip(yt, yp))
    fn = sum(a and not b for a, b in zip(yt, yp))
    fp = sum((not a) and b for a, b in zip(yt, yp))
    tn = sum((not a) and (not b) for a, b in zip(yt, yp))
    return {
        "n": len(yt),
        "accuracy": round(accuracy_score(yt, yp), 4),
        "precision_escalate": round(precision_score(yt, yp, zero_division=0), 4),
        "recall_escalate": round(recall_score(yt, yp, zero_division=0), 4),
        "f1_escalate": round(f1_score(yt, yp, zero_division=0), 4),
        "missed_escalations": fn,
        "needless_escalations": fp,
        "auto_rate": round(sum(1 for p in pred if p == "auto") / max(len(pred), 1), 4),
        "counts": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def kappa(a: list, b: list) -> float:
    """Cohen's kappa — agreement corrected for what chance alone would produce."""
    return round(cohen_kappa_score(a, b), 4)
