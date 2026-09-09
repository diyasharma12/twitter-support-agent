"""Build the deterministic subsample of threads that gets committed to data/sample/."""
import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.data.sample import filter_threads, load_threads, sample_threads, write_sample

if __name__ == "__main__":
    cfg = load_config()
    brand = cfg["brand"]
    if not brand:
        raise SystemExit("Set `brand:` in config.yaml first (run `make profile`).")

    threads_path = resolve(cfg["data"]["threads_jsonl"], brand=brand)
    if not threads_path.exists():
        raise SystemExit(f"Missing {threads_path}. Run `make threads` first.")
    out_path = resolve(cfg["data"]["sample_jsonl"], brand=brand)

    threads = load_threads(threads_path)
    kept = filter_threads(threads)
    sampled = sample_threads(kept, cfg["data"]["sample_size"], cfg["random_seed"])
    n = write_sample(sampled, out_path)
    print(
        f"Kept {len(kept):,}/{len(threads):,} threads after filtering; "
        f"sampled {n:,} -> {out_path}"
    )
