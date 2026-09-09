"""The single door to the LLM.

Why a wrapper instead of calling the SDK directly:
  * Free-tier quota is the binding constraint on this project. Every prompt/response pair
    is cached on disk by hash, so re-running the eval costs zero API calls and the
    published results are reproducible without a key (if the cache is present).
  * A shared rate limiter keeps us under the free-tier requests-per-minute ceiling.
  * One place to add retries, so transient 429/503s do not kill a 200-example eval run.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

from .config import REPO_ROOT, load_config, require_api_key


class RateLimiter:
    """Crude but sufficient: never start more than N requests per rolling minute."""

    def __init__(self, per_minute: int):
        self.min_interval = 60.0 / max(per_minute, 1)
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            gap = time.monotonic() - self._last
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
            self._last = time.monotonic()


class LLM:
    def __init__(self, cfg: dict | None = None):
        self.cfg = (cfg or load_config())["llm"]
        self.cache_dir = REPO_ROOT / self.cfg["cache_dir"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.limiter = RateLimiter(self.cfg["requests_per_minute"])
        self._client = None  # lazy: a cache-only run needs no key

    def _model(self, temperature: float):
        import google.generativeai as genai

        if self._client is None:
            genai.configure(api_key=require_api_key())
            self._client = genai
        return self._client.GenerativeModel(
            self.cfg["model"],
            generation_config={
                "temperature": temperature,
                "max_output_tokens": self.cfg["max_output_tokens"],
            },
        )

    def _cache_path(self, prompt: str, temperature: float) -> Path:
        key = hashlib.sha256(
            json.dumps(
                {"m": self.cfg["model"], "t": temperature, "p": prompt}, sort_keys=True
            ).encode()
        ).hexdigest()
        return self.cache_dir / f"{key}.json"

    def complete(self, prompt: str, temperature: float = 0.0, use_cache: bool = True) -> str:
        """Return the model's text for `prompt`, hitting the disk cache when possible."""
        path = self._cache_path(prompt, temperature)
        if use_cache and path.exists():
            return json.loads(path.read_text())["response"]

        last_err: Exception | None = None
        for attempt in range(5):
            try:
                self.limiter.wait()
                resp = self._model(temperature).generate_content(prompt)
                text = (resp.text or "").strip()
                path.write_text(json.dumps({"prompt": prompt, "response": text}))
                return text
            except Exception as err:  # noqa: BLE001 - free tier throws several shapes
                last_err = err
                time.sleep(2**attempt)
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def complete_json(self, prompt: str, temperature: float = 0.0) -> dict:
        """Same, but strips markdown fences and parses JSON. Raises on unparseable output.

        Unparseable output is itself a finding worth reporting, so we do not silently
        repair it here — the caller decides whether to count it as a failure.
        """
        raw = self.complete(prompt, temperature=temperature)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            cleaned = cleaned[4:] if cleaned.startswith("json") else cleaned
        return json.loads(cleaned.strip())
