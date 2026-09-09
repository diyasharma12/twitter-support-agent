"""Print per-brand stats so we can choose one brand on evidence, not vibes."""
import _bootstrap  # noqa: F401
from support_agent.config import load_config, resolve
from support_agent.data.profile import brand_stats

if __name__ == "__main__":
    cfg = load_config()
    stats = brand_stats(resolve(cfg["data"]["index_db"]))
    hdr = f"{'brand':<20}{'replies':>10}{'avg chars':>11}{'DM-deflect':>12}"
    print(hdr)
    print("-" * len(hdr))
    for s in stats:
        print(
            f"{s['brand']:<20}{s['replies']:>10,}{s['avg_reply_chars']:>11}"
            f"{s['dm_deflection_share']:>12.1%}"
        )
