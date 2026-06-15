"""HTTP client with disk cache and rate limiting.

Uses *curl_cffi* with browser impersonation to bypass Cloudflare.
"""

import hashlib
import time
from pathlib import Path

from curl_cffi import requests as curl_requests

from scraper.config import (
    BASE_URL,
    CACHE_DIR,
    CACHE_TTL,
    HEADERS,
    MAX_RETRIES,
    REQUEST_DELAY,
    RETRY_BACKOFF,
)

IMPRESONATE = "chrome124"


class HltvHttpClient:
    """Lightweight HTTP wrapper around HLTV.org with disk cache & rate limiting."""

    def __init__(self) -> None:
        self._session = curl_requests.Session()
        self._session.headers.update(HEADERS)
        self._last_request: float = 0.0

    def get(self, path: str, force: bool = False) -> str:
        url = f"{BASE_URL}{path}"
        cache_file = self._cache_path(url)

        if not force and cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < CACHE_TTL:
                return cache_file.read_text(encoding="utf-8")

        self._throttle()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._session.get(
                    url,
                    impersonate=IMPRESONATE,
                    timeout=30,
                )
                resp.raise_for_status()
                html = resp.text
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(html, encoding="utf-8")
                return html
            except Exception as exc:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF**attempt)
                else:
                    raise RuntimeError(
                        f"Failed to fetch {url} " f"after {MAX_RETRIES} attempts"
                    ) from exc

        raise RuntimeError(f"Failed to fetch {url} — all attempts exhausted")

    def close(self) -> None:
        self._session.close()

    @staticmethod
    def _cache_path(url: str) -> Path:
        raw = url.removeprefix(BASE_URL).lstrip("/") or "index"
        safe = raw.replace("/", "_").replace("?", "_").replace("&", "_")
        if len(safe) > 120:
            suffix = hashlib.md5(raw.encode()).hexdigest()[:8]
            safe = safe[:100] + "_" + suffix
        return CACHE_DIR / f"{safe}.html"

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request = time.time()

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.close()
