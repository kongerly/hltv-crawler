# HLTV CS2 Crawler

> CS2 match data crawler — scrape HLTV matches, maps, player stats to SQLite.

## Features

- **Cloudflare bypass** via `curl_cffi` (Chrome 124 impersonation)
- **Disk cache** — avoid re-downloading (24h TTL)
- **Rate limiting** — 2s between requests
- **Pagination** — auto-scroll through results pages
- **Date/event filtering** — scrape only what you need
- **Resume support** — stop and continue later (via `progress.json`)
- **Zero external deps for storage** — SQLite is Python stdlib

## Quick Start

```bash
# 1. Install
git clone git@github.com:kongerly/hltv-crawler.git
cd hltv-crawler
python -m venv .venv
.venv\\Scripts\\activate      # Windows
pip install -r requirements.txt

# 2. Crawl (use --max-pages first to test)
python crawl.py --max-pages=3

# 3. More examples
python crawl.py --max-pages=10 --start-date=2025-01-01
python crawl.py --event="IEM" --max-pages=5
python crawl.py --resume                      # Continue from last time
```

## Output

- `data/hltv.db` — SQLite database with 6 tables
- `data/raw/*.html` — cached HTML pages (can be deleted safely)

### Database tables

| Table | Description |
|-------|-------------|
| `events` | Tournaments & events |
| `teams` | Team rankings |
| `players` | Player roster info |
| `matches` | Match results (bo, scores, winner) |
| `maps` | Per-map scores + CT/T side rounds |
| `player_match_stats` | Per-player stats (rating, ADR, KAST, K/D) |

## Requirements

- Python 3.10+
- `curl_cffi` — HTTP client with TLS fingerprint spoofing
- `beautifulsoup4` — HTML parsing

## Use as a Library

```python
from pathlib import Path
from storage import Database
from scraper import HltvOrchestrator

with Database(Path("data/hltv.db")) as db:
    db.create_tables()
    with HltvOrchestrator(db) as orch:
        counts = orch.run_full_pipeline(max_pages=5)
        print(counts)
```

## License

MIT
