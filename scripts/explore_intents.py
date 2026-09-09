"""Print clusters of real customer messages so you can define the intent taxonomy.

Usage: python scripts/explore_intents.py [k] [examples_per_cluster]
Read the examples. Then write your taxonomy into src/support_agent/intents.py.
"""
import sys
import textwrap

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.data.explore import cluster, load_sample

if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    cfg = load_config()
    threads = load_sample(resolve(cfg["data"]["sample_jsonl"], brand=cfg["brand"]))
    labels, top_terms = cluster(threads, k, cfg["random_seed"])

    for c in range(k):
        members = [t for t, lab in zip(threads, labels) if lab == c]
        print("=" * 78)
        print(f"CLUSTER {c}  ({len(members)} of {len(threads)})  :: {', '.join(top_terms[c])}")
        print("=" * 78)
        for t in members[:per]:
            print("  C:", textwrap.shorten(t["customer_message"], 160))
            print("  B:", textwrap.shorten(t.get("brand_reply") or "(no reply)", 160))
            print()
