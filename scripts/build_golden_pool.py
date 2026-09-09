"""Pick WHICH threads go into the golden set, before any of them are labelled.

Sampling strategy (this paragraph goes in the report):
  * Stratify by TF-IDF cluster, proportional to cluster size but with a floor of 8 per
    cluster, so small-but-real issue types survive into the evaluation set. A purely
    random 200 would be dominated by the two biggest clusters and would flatter any
    model that only learns those.
  * Within a stratum, sample uniformly at random with the project seed.
  * Only threads that HAVE a brand reply are eligible, since reply quality cannot be
    scored without a reference.
  * The pool is frozen and committed before labelling starts, so there is no chance of
    quietly dropping examples that turn out to be inconvenient.
"""
import json
import random

import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.data.explore import cluster, load_sample

POOL_SIZE = 200
FLOOR_PER_CLUSTER = 8
K = 10

if __name__ == "__main__":
    cfg = load_config()
    seed = cfg["random_seed"]
    threads = load_sample(resolve(cfg["data"]["sample_jsonl"], brand=cfg["brand"]))
    eligible = [t for t in threads if (t.get("brand_reply") or "").strip()]
    labels, _ = cluster(eligible, K, seed)
    for t, lab in zip(eligible, labels):
        t["_cluster"] = int(lab)

    by_cluster: dict[int, list[dict]] = {}
    for t in eligible:
        by_cluster.setdefault(t["_cluster"], []).append(t)

    rng = random.Random(seed)
    quotas = {}
    remaining = POOL_SIZE - FLOOR_PER_CLUSTER * len(by_cluster)
    total = len(eligible)
    for c, members in by_cluster.items():
        quotas[c] = FLOOR_PER_CLUSTER + int(remaining * len(members) / total)

    pool = []
    for c, members in sorted(by_cluster.items()):
        take = min(quotas[c], len(members))
        pool.extend(rng.sample(sorted(members, key=lambda t: t["thread_id"]), take))
    rng.shuffle(pool)
    pool = pool[:POOL_SIZE]

    out = resolve("data/golden/pool.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for t in pool:
            fh.write(json.dumps(t) + "\n")
    print(f"Froze a labelling pool of {len(pool)} threads -> {out}")
    print("Per-cluster counts:", {c: sum(1 for t in pool if t['_cluster'] == c)
                                  for c in sorted(by_cluster)})
