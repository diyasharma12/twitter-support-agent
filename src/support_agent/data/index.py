"""Turn the 3M-row Kaggle CSV into a sqlite index we can query without loading it all.

Why sqlite and not "just use pandas": the raw file is ~500MB and thread reconstruction
needs random access by tweet_id. Holding the whole frame plus a dict index comfortably
exceeds a laptop's memory, and every experiment would pay a 60-second reload. One
streaming pass into sqlite makes every later step cheap and interruptible.
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tweets (
    tweet_id              INTEGER PRIMARY KEY,
    author_id             TEXT NOT NULL,
    inbound               INTEGER NOT NULL,   -- 1 = from a customer, 0 = from a brand
    created_at            TEXT,
    text                  TEXT,
    response_tweet_id     TEXT,               -- comma-separated ids, may be empty
    in_response_to_tweet_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_author ON tweets(author_id);
CREATE INDEX IF NOT EXISTS idx_parent ON tweets(in_response_to_tweet_id);
"""


def _rows(csv_path: Path):
    csv.field_size_limit(sys.maxsize)
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                tweet_id = int(row["tweet_id"])
            except (TypeError, ValueError):
                continue  # a handful of malformed rows exist; skipping them is logged
            parent = row.get("in_response_to_tweet_id") or ""
            yield (
                tweet_id,
                row["author_id"],
                1 if str(row["inbound"]).lower() == "true" else 0,
                row.get("created_at"),
                row.get("text"),
                row.get("response_tweet_id") or "",
                int(parent) if parent.isdigit() else None,
            )


def build_index(csv_path: Path, db_path: Path, batch: int = 50_000) -> int:
    """Stream the CSV into sqlite. Returns the number of rows inserted."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    inserted, buf = 0, []
    for row in _rows(csv_path):
        buf.append(row)
        if len(buf) >= batch:
            conn.executemany("INSERT OR REPLACE INTO tweets VALUES (?,?,?,?,?,?,?)", buf)
            conn.commit()
            inserted += len(buf)
            buf.clear()
            print(f"  indexed {inserted:,} rows", end="\r", flush=True)
    if buf:
        conn.executemany("INSERT OR REPLACE INTO tweets VALUES (?,?,?,?,?,?,?)", buf)
        conn.commit()
        inserted += len(buf)
    conn.close()
    print(f"  indexed {inserted:,} rows")
    return inserted
