<p align="center">
  <img src="https://img.shields.io/pypi/v/hltv-crawler?style=flat-square" alt="PyPI">
  <img src="https://img.shields.io/pypi/pyversions/hltv-crawler?style=flat-square" alt="Python">
  <img src="https://img.shields.io/github/actions/workflow/status/kongerly/hltv-crawler/ci.yml?branch=main&style=flat-square" alt="CI">
  <img src="https://img.shields.io/github/license/kongerly/hltv-crawler?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/database-SQLite-green?style=flat-square&logo=sqlite" alt="DB">
</p>

# hltv-crawler

> HLTV CS2 match data crawler - scrape matches, maps, and player stats into SQLite.
>
> Bypasses Cloudflare. Caches aggressively. Resumes interrupted crawls.

## Features

- **Cloudflare bypass** - uses `curl_cffi` with Chrome 124 TLS fingerprint
- **Disk cache** - avoids re-downloading HTML (24h TTL, configurable)
- **Rate limiting** - 2s between requests to reduce request pressure
- **Pagination** - iterates result pages automatically
- **Filter by date / event** - scrape only the matches you need
- **Resume support** - stop anytime and continue later via `--resume`
- **SQLite storage** - 6 normalized tables, zero external storage dependencies
- **Pure Python** - Python 3.10+, no heavy data stack required

## Install

### Runtime install

```bash
pip install hltv-crawler
```

### Local development install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r deps/dev.txt
```

Alternative editable install:

```bash
python -m pip install -e .[dev]
```

## Quick Start

### CLI

```bash
# Crawl recent matches (20 pages, about 1000 matches)
hltv-crawler

# Limit to 3 pages for a quick test
hltv-crawler --max-pages=3

# Filter by date range
hltv-crawler --start-date=2025-01-01 --end-date=2025-06-01

# Filter by event
hltv-crawler --event="IEM"

# Scrape a specific event by ID (no name ambiguity)
hltv-crawler --event-id 7732

# Scrape a specific team at an event by ID
hltv-crawler --event-id 7732 --team-id 4608

# Scrape a specific player at an event by ID
hltv-crawler --event-id 7732 --player-id 12345

# Scrape by event/team/player name (resolves to ID)
hltv-crawler --event "IEM Cologne" --team "Spirit"
hltv-crawler --event "IEM Cologne" --player "donk"

# Resume an interrupted crawl
hltv-crawler --resume

# Ignore cache and force re-fetch
hltv-crawler --force
```

### Python API

```python
from pathlib import Path

from scraper import HltvOrchestrator
from storage import Database

with Database(Path("data/hltv.db")) as db:
    db.create_tables()
    with HltvOrchestrator(db) as orch:
        counts = orch.run_full_pipeline(
            max_pages=5,
            start_date="2025-01-01",
            event_name="IEM",
        )
        print(counts)
        # {'events': 88, 'team_rankings': 248, 'players': 1283,
        #  'maps': 15, 'player_stats': 56, 'detail_scraped': 5}
```

## Output

### Database: `data/hltv.db`

6 normalized tables with foreign key constraints:

| Table | Rows (approx) | Description |
|-------|---------------|-------------|
| `events` | 88 | Tournaments and events |
| `teams` | 248 | Team rankings with world rank |
| `players` | 1283 | Player info with team affiliation |
| `matches` | 2550 | Match results (teams, scores, bo, winner) |
| `maps` | 404 | Per-map scores and CT/T side round breakdown |
| `player_match_stats` | 1345 | Per-player stats (rating, ADR, KAST, K/D) |

### Cache: `data/raw/*.html`

Raw HTML is cached to disk. It is safe to delete cached files; the crawler will fetch them again on the next run.

## All CLI Options

```text
--force                  Ignore disk cache, re-fetch all pages
--max-matches N          Max match details to scrape (default: all)
--max-pages N            Max result pages to scrape (50 matches/page, default: 20)
--start-date YYYY-MM-DD  Only matches on or after this date
--end-date YYYY-MM-DD    Only matches on or before this date
--event NAME             Filter by event name in pipeline mode, or resolve
                         to event ID for targeted scraping
                         (prefers exact match; on multiple matches
                          lists all and exits with guidance)
--event-id ID            Scrape a specific event by ID (no ambiguity)
--team-id ID             Scrape a specific team at an event (requires --event-id)
--player-id ID           Scrape a specific player at an event (requires --event-id)
--team NAME              Resolve and scrape team by name (requires --event/--event-id)
--player NAME            Resolve and scrape player by name (requires --event/--event-id)
--resume                 Resume from last saved progress
```

Targeted scraping modes:

- `--event-id <ID>` - scrape all matches for a specific tournament
- `--event-id <ID> --team-id <ID>` - scrape one team's matches at a tournament
- `--event-id <ID> --player-id <ID>` - scrape one player's matches at a tournament
- `--event <NAME>` - resolve event name to ID and scrape all its matches
- `--event <NAME> --team <NAME>` - resolve both by name and scrape team at event
- `--event <NAME> --player <NAME>` - resolve both by name and scrape player at event

> **Note**: If `--event` matches multiple tournaments, such as `"IEM Dallas"` matching both `IEM Dallas 2024` and `IEM Dallas 2025`, the tool lists all matches and exits with guidance. Include the year in the name or use `--event-id` to disambiguate.

## Development

### Quality tools

This repository uses:

- `ruff` for linting and formatting
- `pre-commit` for local quality checks before commit
- `pytest` for parser and storage tests
- GitHub Actions for CI on push and pull request

### Common commands

```bash
# Run lint
python -m ruff check .

# Apply formatting
python -m ruff format .

# Run tests
python -m pytest

# Install git hooks locally
pre-commit install

# Run all configured hooks manually
pre-commit run --all-files
```

### CI

GitHub Actions workflow: `.github/workflows/ci.yml`

The CI pipeline currently runs on:

- `push`
- `pull_request`

And checks:

- Python `3.10`
- Python `3.13`
- `ruff check .`
- `ruff format --check .`
- `pytest`

## Use Cases

- **Esports analysts** - build a local database of pro CS2 matches
- **ML / prediction** - collect training data for match outcome prediction
- **Content creators** - support data-driven CS2 analysis
- **Data engineers** - reference implementation for scraping and SQLite pipelines

## Requirements

- Python 3.10+
- `curl_cffi` - HTTP client with TLS fingerprint spoofing
- `beautifulsoup4` - HTML parsing

## License

MIT
