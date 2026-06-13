"""Scraper configuration — URLs, headers, rate limits, cache settings."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "raw"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.hltv.org"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

REQUEST_DELAY = 2.0
CACHE_TTL = 86400
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0
