"""One-time: stream data/raw/twcs.csv into a sqlite index."""
import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.data.index import build_index

if __name__ == "__main__":
    cfg = load_config()
    csv_path = resolve(cfg["data"]["raw_csv"])
    db_path = resolve(cfg["data"]["index_db"])
    if not csv_path.exists():
        raise SystemExit(f"Missing {csv_path}. Download the Kaggle CSV into data/raw/.")
    print(f"Indexing {csv_path} -> {db_path}")
    build_index(csv_path, db_path)
