"""Thread reconstruction is the one place a silent bug would poison every later number,
so it gets a hand-built fixture with a known answer."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from support_agent.data.index import SCHEMA
from support_agent.data.threads import clean, iter_threads


def _db(tmp_path, rows):
    path = tmp_path / "t.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO tweets VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return path


def test_simple_two_turn_thread(tmp_path):
    rows = [
        (1, "12345", 1, "t0", "@Brand my order never arrived", "2", None),
        (2, "Brand", 0, "t1", "@12345 sorry! can you share your order id?", "3", 1),
        (3, "12345", 1, "t2", "@Brand it is AB-99", "", 2),
    ]
    db = _db(tmp_path, rows)
    threads = list(iter_threads(db, "Brand"))
    assert len(threads) == 1
    t = threads[0]
    assert t.first_customer_message == "my order never arrived"
    assert t.first_brand_reply == "sorry! can you share your order id?"
    assert len(t.turns) == 3


def test_clean_strips_handles_but_keeps_urls():
    assert clean("@Brand help https://x.co/a") == "help https://x.co/a"
