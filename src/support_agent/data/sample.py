"""Builds the committed subsample the grader actually runs against.

Sampling straight off the reconstructed threads would drag in junk the rest of the
pipeline was never designed for: near-empty "help" tweets and non-English customers
the classifier/judge can't be expected to handle. Filtering first, then sorting by
thread_id before sampling, means the same `random_seed` in config.yaml always picks
the same thread_ids, regardless of what order `build_threads.py` happened to emit them.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

MIN_MESSAGE_LEN = 15

_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")
_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def is_english_looking(text: str) -> bool:
    """Cheap heuristic (no NLP deps): mostly ASCII, with a healthy share of Latin letters."""
    if not text:
        return False
    non_ascii_share = len(_NON_ASCII_RE.findall(text)) / len(text)
    if non_ascii_share > 0.2:
        return False
    letter_share = len(_LATIN_LETTER_RE.findall(text)) / len(text)
    return letter_share > 0.3


def load_threads(jsonl_path: Path) -> list[dict]:
    threads = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                threads.append(json.loads(line))
    return threads


def filter_threads(threads: list[dict]) -> list[dict]:
    """Drop threads whose customer message is too short or doesn't look English."""
    kept = []
    for t in threads:
        msg = t.get("customer_message") or ""
        if len(msg) < MIN_MESSAGE_LEN:
            continue
        if not is_english_looking(msg):
            continue
        kept.append(t)
    return kept


def sample_threads(threads: list[dict], sample_size: int, seed: int) -> list[dict]:
    """Deterministic sample: fix input order by thread_id, then seed a private RNG."""
    ordered = sorted(threads, key=lambda t: t["thread_id"])
    if sample_size >= len(ordered):
        return ordered
    rng = random.Random(seed)
    return rng.sample(ordered, sample_size)


def write_sample(threads: list[dict], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for t in threads:
            fh.write(json.dumps(t) + "\n")
    return len(threads)
