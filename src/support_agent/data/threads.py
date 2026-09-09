"""Reconstruct customer<->brand conversations from the flat tweet table.

The dataset is a forest, not a list: a row points at its parent via
`in_response_to_tweet_id` and at its children via a comma-separated `response_tweet_id`.
A "thread" here is the chain from a customer's opening tweet through the alternating
replies, kept only when the brand we care about actually participated.

Definition choices (worth defending in the report):
  * The FIRST inbound tweet of a thread is the message the agent must handle. Later
    customer turns often depend on the brand's reply, which would leak the answer.
  * The brand's first substantive reply is the reference reply.
  * Threads with no brand reply are kept separately: they are real traffic, but they
    cannot be scored for reply quality.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path

HANDLE_RE = re.compile(r"@\w+")


@dataclass
class Turn:
    tweet_id: int
    author_id: str
    inbound: bool
    created_at: str | None
    text: str


@dataclass
class Thread:
    thread_id: int
    brand: str
    turns: list[Turn] = field(default_factory=list)

    @property
    def first_customer_message(self) -> str | None:
        for t in self.turns:
            if t.inbound:
                return t.text
        return None

    @property
    def first_brand_reply(self) -> str | None:
        for t in self.turns:
            if not t.inbound and t.author_id == self.brand:
                return t.text
        return None


def clean(text: str | None) -> str:
    """Strip @handles and collapse whitespace. Keeps URLs — 'we sent a link' matters."""
    if not text:
        return ""
    return HANDLE_RE.sub("", text).strip()


def _children(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


def iter_threads(db_path: Path, brand: str, max_turns: int = 12):
    """Yield Thread objects for every conversation `brand` participated in."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    roots = conn.execute(
        """
        SELECT DISTINCT parent.*
        FROM tweets AS reply
        JOIN tweets AS parent ON parent.tweet_id = reply.in_response_to_tweet_id
        WHERE reply.author_id = ? AND reply.inbound = 0 AND parent.inbound = 1
        """,
        (brand,),
    ).fetchall()

    for root in roots:
        # Walk back to the true start of the conversation.
        start = root
        seen = {start["tweet_id"]}
        while start["in_response_to_tweet_id"]:
            prev = conn.execute(
                "SELECT * FROM tweets WHERE tweet_id = ?",
                (start["in_response_to_tweet_id"],),
            ).fetchone()
            if prev is None or prev["tweet_id"] in seen:
                break
            seen.add(prev["tweet_id"])
            start = prev

        turns, node = [], start
        while node is not None and len(turns) < max_turns:
            turns.append(
                Turn(
                    tweet_id=node["tweet_id"],
                    author_id=node["author_id"],
                    inbound=bool(node["inbound"]),
                    created_at=node["created_at"],
                    text=clean(node["text"]),
                )
            )
            kids = _children(node["response_tweet_id"])
            node = None
            for kid in kids:
                nxt = conn.execute(
                    "SELECT * FROM tweets WHERE tweet_id = ?", (kid,)
                ).fetchone()
                if nxt is not None and nxt["tweet_id"] not in seen:
                    seen.add(nxt["tweet_id"])
                    node = nxt
                    break

        thread = Thread(thread_id=start["tweet_id"], brand=brand, turns=turns)
        if thread.first_customer_message:
            yield thread
    conn.close()


def write_jsonl(threads, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for t in threads:
            fh.write(
                json.dumps(
                    {
                        "thread_id": t.thread_id,
                        "brand": t.brand,
                        "customer_message": t.first_customer_message,
                        "brand_reply": t.first_brand_reply,
                        "turns": [asdict(x) for x in t.turns],
                    }
                )
                + "\n"
            )
            n += 1
    return n
