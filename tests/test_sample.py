"""Sampling must be reproducible - the committed sample is only trustworthy if the
same seed always picks the same threads."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from support_agent.data.sample import filter_threads, is_english_looking, sample_threads


def _thread(thread_id, customer_message):
    return {
        "thread_id": thread_id,
        "brand": "Brand",
        "customer_message": customer_message,
        "brand_reply": None,
        "turns": [],
    }


def test_filter_drops_short_and_non_english_and_missing():
    threads = [
        _thread(1, "help"),  # too short
        _thread(2, "my order never arrived, please help"),  # keep
        _thread(3, "オーダーが届きません、助けてください"),  # non-English
        _thread(4, None),  # missing message
    ]
    kept = filter_threads(threads)
    assert [t["thread_id"] for t in kept] == [2]


def test_sample_is_deterministic_for_same_seed():
    threads = [_thread(i, f"my order {i} never arrived please help") for i in range(50)]
    first = sample_threads(threads, sample_size=10, seed=42)
    second = sample_threads(threads, sample_size=10, seed=42)
    assert [t["thread_id"] for t in first] == [t["thread_id"] for t in second]


def test_sample_differs_for_different_seed():
    threads = [_thread(i, f"my order {i} never arrived please help") for i in range(50)]
    a = [t["thread_id"] for t in sample_threads(threads, sample_size=10, seed=1)]
    b = [t["thread_id"] for t in sample_threads(threads, sample_size=10, seed=2)]
    assert a != b


def test_is_english_looking():
    assert is_english_looking("please help me with my order") is True
    assert is_english_looking("请帮我处理订单问题谢谢") is False
    assert is_english_looking("") is False
