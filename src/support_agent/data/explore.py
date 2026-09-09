"""Cluster customer messages so a human can READ the data efficiently.

This is a reading aid, not a labeller. K-means over TF-IDF finds surface-level groupings;
the intent taxonomy is a human judgement made after reading real examples. Clusters are
used for one more thing though: stratifying the golden-set pool, so rare-but-real issue
types are not drowned out by "where is my bag".
"""
from __future__ import annotations

import json
from pathlib import Path

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def load_sample(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def cluster(threads: list[dict], k: int, seed: int):
    """Return (labels, top_terms_per_cluster). Adds nothing to the threads themselves."""
    texts = [t["customer_message"] for t in threads]
    vec = TfidfVectorizer(
        max_features=5000, stop_words="english", ngram_range=(1, 2), min_df=3
    )
    X = vec.fit_transform(texts)
    km = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(X)
    terms = vec.get_feature_names_out()
    top = []
    for centre in km.cluster_centers_:
        top.append([terms[i] for i in centre.argsort()[::-1][:8]])
    return km.labels_, top
