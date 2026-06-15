"""HLTV CS2 Match Data Crawler.

Scrape match data from HLTV and store to local SQLite database.
Supports pagination, date range filtering, event filtering, resume,
and targeted scraping (event / team / player at event).

Usage:
    python crawl.py                                          # default: scrape recent 20 pages
    python crawl.py --event-id 7732                          # scrape all matches for event ID 7732
    python crawl.py --event-id 7732 --team-id 4608           # scrape team at event
    python crawl.py --event-id 7732 --player-id 12345        # scrape player at event

Examples:
    python crawl.py                              # 爬取最近20页结果
    python crawl.py --max-pages=5                # 只爬5页
    python crawl.py --start-date=2025-01-01      # 2025年后的比赛
    python crawl.py --event="IEM"                # 只爬IEM赛事
    python crawl.py --resume                     # 断点续爬
    python crawl.py --event-id 7732               # 指定赛事全部比赛数据
    python crawl.py --event-id 7732 --team-id 4608 # 指定队伍在指定赛事
    python crawl.py --event-id 7732 --player-id 12345 # 指定选手在指定赛事
    python crawl.py --event "IEM Cologne"              # 按名字爬取赛事
    python crawl.py --event "IEM Cologne" --team "Spirit" # 队伍在指定赛事(按名字)
    python crawl.py --event "IEM Cologne" --player "donk" # 选手在指定赛事(按名字)
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
    parser = argparse.ArgumentParser(description="HLTV CS2 match data crawler")
    parser.add_argument(
        "--force", action="store_true", help="Ignore disk cache and re-fetch all pages"
    )
    parser.add_argument(
        "--max-matches",
        type=int,
        default=None,
        help="Max match details to scrape (None = all)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Max result pages to scrape (50 matches per page)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Only matches on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Only matches on or before this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--event",
        type=str,
        default=None,
        help="Scrape event by name (substring match, resolves to ID)",
    )
    parser.add_argument(
        "--event-id", type=int, default=None, help="Scrape a specific event by ID"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from last saved progress"
    )
    parser.add_argument(
        "--team-id",
        type=int,
        default=None,
        help="Scrape a specific team at an event (requires --event-id)",
    )
    parser.add_argument(
        "--player-id",
        type=int,
        default=None,
        help="Scrape a specific player at an event (requires --event-id)",
    )
    parser.add_argument(
        "--team",
        type=str,
        default=None,
        help="Scrape team at event by name (requires --event/--event-id)",
    )
    parser.add_argument(
        "--player",
        type=str,
        default=None,
        help="Scrape player at event by name (requires --event/--event-id)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    db_path = Path("data") / "hltv.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with Database(db_path) as db:
        db.create_tables()
        logger.info("Database ready at %s", db_path.resolve())

        with HltvOrchestrator(db) as orch:
            # Resolve name-based args to IDs
            event_id = args.event_id
            if event_id is None and args.event:
                event_id = orch._resolve_event_by_name(args.event)
                if event_id is None:
                    logger.error(
                        "Cannot resolve event '%s'. "
                        "Check logs above for matching events or use --event-id.",
                        args.event,
                    )
                    sys.exit(1)
                logger.info("Resolved event name '%s' -> ID %d", args.event, event_id)

            team_id = args.team_id
            if team_id is None and args.team:
                team_id = orch._resolve_team_by_name(args.team)
                if team_id is None:
                    logger.error("Cannot find team matching '%s'", args.team)
                    sys.exit(1)
                logger.info("Resolved team name '%s' -> ID %d", args.team, team_id)

            player_id = args.player_id
            if player_id is None and args.player:
                player_id = orch._resolve_player_by_name(args.player)
                if player_id is None:
                    logger.error("Cannot find player matching '%s'", args.player)
                    sys.exit(1)
                logger.info(
                    "Resolved player name '%s' -> ID %d", args.player, player_id
                )

            # --- 1) Player at event mode ---
            if player_id is not None:
                if event_id is None:
                    logger.error("--player/--player-id requires --event/--event-id")
                    sys.exit(1)
                counts = orch.scrape_player_at_event(
                    player_id=player_id,
                    event_id=event_id,
                    force=args.force,
                )

            # --- 2) Team at event mode ---
            elif team_id is not None:
                if event_id is None:
                    logger.error("--team/--team-id requires --event/--event-id")
                    sys.exit(1)
                counts = orch.scrape_team_at_event(
                    team_id=team_id,
                    event_id=event_id,
                    force=args.force,
                )

            # --- 3) Event scrape mode ---
            elif event_id is not None:
                counts = orch.scrape_event_by_id(
                    event_id=event_id,
                    force=args.force,
                    max_matches=args.max_matches,
                )

            # --- 4) Default pipeline (results page + filters) ---
            else:
                event_name = args.event
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
