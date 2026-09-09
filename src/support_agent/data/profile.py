"""Per-brand statistics, used once to choose which brand to build the agent for.

The choice matters more than it looks: a brand whose replies are almost all
"DM us and we'll help" gives an agent nothing to ground a draft in, however much data it
has. So we report not just volume but reply substance.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# Deflection is any reply that moves the customer to another channel instead of
# answering. The first version of this only looked for "DM", which badly undercounted
# brands that push people to phone/chat/email instead — AmazonHelp scored 1.2% while
# its replies were visibly full of "reach us by phone or chat here". See DECISIONS.md #8.
DM_MARKERS = (
    "dm ",
    "dm us",
    "direct message",
    "send us a message",
    "pm us",
    "by phone",
    "phone or chat",
    "give us a call",
    "call us",
    "contact us at",
    "email us",
    "reach us",
    "chat here",
)


def brand_stats(db_path: Path, top_n: int = 25) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT author_id AS brand,
               COUNT(*)                                    AS replies,
               AVG(LENGTH(text))                           AS avg_reply_chars,
               SUM(CASE WHEN in_response_to_tweet_id IS NOT NULL THEN 1 ELSE 0 END)
                                                           AS replies_to_a_customer
        FROM tweets
        WHERE inbound = 0
        GROUP BY author_id
        ORDER BY replies DESC
        LIMIT ?
        """,
        (top_n,),
    ).fetchall()

    out = []
    for r in rows:
        texts = conn.execute(
            "SELECT text FROM tweets WHERE author_id = ? AND inbound = 0 LIMIT 500",
            (r["brand"],),
        ).fetchall()
        lowered = [(t["text"] or "").lower() for t in texts]
        dm_share = (
            sum(any(m in t for m in DM_MARKERS) for t in lowered) / len(lowered)
            if lowered
            else 0.0
        )
        out.append(
            {
                "brand": r["brand"],
                "replies": r["replies"],
                "avg_reply_chars": round(r["avg_reply_chars"] or 0, 1),
                "replies_to_a_customer": r["replies_to_a_customer"],
                "dm_deflection_share": round(dm_share, 3),
            }
        )
    conn.close()
    return out
