"""Reconstruct all threads for the configured brand into JSONL."""
import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.data.threads import iter_threads, write_jsonl

if __name__ == "__main__":
    cfg = load_config()
    brand = cfg["brand"]
    if not brand:
        raise SystemExit("Set `brand:` in config.yaml first (run `make profile`).")
    db = resolve(cfg["data"]["index_db"])
    out = resolve(cfg["data"]["threads_jsonl"], brand=brand)
    n = write_jsonl(iter_threads(db, brand), out)
    print(f"Wrote {n:,} threads for {brand} -> {out}")
