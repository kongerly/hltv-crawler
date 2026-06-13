"""HLTV CS2 Match Data Crawler.

Scrape match data from HLTV and store to local SQLite database.
Supports pagination, date range filtering, event filtering, and resume.

Usage:
    python crawl.py [--max-pages=N] [--start-date=YYYY-MM-DD]
                    [--end-date=YYYY-MM-DD] [--event=NAME]
                    [--event-id=ID] [--force] [--resume]

Examples:
    python crawl.py                              # 爬取最近20页结果
    python crawl.py --max-pages=5                # 只爬5页
    python crawl.py --start-date=2025-01-01      # 2025年后的比赛
    python crawl.py --event="IEM"                # 只爬IEM赛事
    python crawl.py --resume                     # 断点续爬
"""

import argparse
import logging
import sys
from pathlib import Path

from scraper import HltvOrchestrator
from storage import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HLTV CS2 match data crawler"
    )
    parser.add_argument("--force", action="store_true",
                        help="Ignore disk cache and re-fetch all pages")
    parser.add_argument("--max-matches", type=int, default=None,
                        help="Max match details to scrape (None = all)")
    parser.add_argument("--max-pages", type=int, default=20,
                        help="Max result pages to scrape (50 matches per page)")
    parser.add_argument("--start-date", type=str, default=None,
                        help="Only matches on or after this date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None,
                        help="Only matches on or before this date (YYYY-MM-DD)")
    parser.add_argument("--event", type=str, default=None,
                        help="Only matches from this event (substring match)")
    parser.add_argument("--event-id", type=int, default=None,
                        help="Only matches from this event ID")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last saved progress")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    db_path = Path("data") / "hltv.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with Database(db_path) as db:
        db.create_tables()
        logger.info("Database ready at %s", db_path.resolve())

        with HltvOrchestrator(db) as orch:
            event_name = args.event
            if args.event_id is not None and event_name is None:
                ev = db.get_event(args.event_id)
                if ev:
                    event_name = ev["event_name"]
                    logger.info("Resolved event_id %d -> %s", args.event_id, event_name)
                else:
                    logger.warning("event_id %d not found", args.event_id)

            counts = orch.run_full_pipeline(
                force=args.force,
                max_matches=args.max_matches,
                start_date=args.start_date,
                end_date=args.end_date,
                event_name=event_name,
                max_pages=args.max_pages,
                resume=args.resume,
            )

    logger.info("Crawl complete — %s", counts)


if __name__ == "__main__":
    main()
