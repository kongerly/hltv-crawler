"""Orchestrator — runs the full scraping pipeline end-to-end."""

import json
import logging
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Optional

from scraper.event_scraper import scrape_events, scrape_event_matches
from scraper.http_client import HltvHttpClient
from scraper.match_scraper import scrape_match_detail, scrape_results_page
from scraper.team_scraper import scrape_ranking_players, scrape_team_rankings
from storage import Database

# Progress tracking for resumable scraping
PROGRESS_FILE = Path("data") / "progress.json"

logger = logging.getLogger(__name__)


class HltvOrchestrator:
    """High-level orchestrator that scrapes HLTV and persists data to SQLite."""

    def __init__(self, db: Database,
                 client: Optional[HltvHttpClient] = None) -> None:
        self._db = db
        self._client = client or HltvHttpClient()

    # ------------------------------------------------------------------
    # Progress persistence
    # ------------------------------------------------------------------

    def _load_progress(self) -> dict[str, Any]:
        """Load scraping progress from disk."""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"last_offset": 0, "scraped_match_ids": [], "failed_match_ids": []}

    def _save_progress(self, progress: dict[str, Any]) -> None:
        """Save scraping progress to disk."""
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def scrape_and_store_events(self, force: bool = False) -> int:
        events = scrape_events(self._client, force=force)
        for ev in events:
            self._db.upsert_event(
                event_id=ev["event_id"],
                event_name=ev["event_name"],
                start_date=ev.get("start_date"),
                end_date=ev.get("end_date"),
            )
        logger.info("Upserted %d events", len(events))
        return len(events)

    # ------------------------------------------------------------------
    # Team rankings
    # ------------------------------------------------------------------

    def scrape_and_store_team_rankings(self, force: bool = False) -> int:
        now = datetime.now(timezone.utc).isoformat()
        teams = scrape_team_rankings(self._client, force=force)
        for t in teams:
            self._db.upsert_team(
                team_id=t["team_id"],
                team_name=t["team_name"],
                world_rank=t.get("world_rank"),
                updated_at=now,
            )
        logger.info("Upserted %d team rankings", len(teams))
        return len(teams)

    # ------------------------------------------------------------------
    # Team detail (player roster)
    # ------------------------------------------------------------------

    def scrape_and_store_team_players(self, team_id: int,
                                      force: bool = False) -> int:
        now = datetime.now(timezone.utc).isoformat()
        # Note: individual team detail pages often return 404.
        # Use scrape_and_store_all_ranking_players() for batch extraction
        # from the ranking page instead.
        logger.warning(
            "Individual team detail scraping disabled (404 issue). "
            "Use scrape_and_store_all_ranking_players() instead."
        )
        return 0

    # ------------------------------------------------------------------
    # Results page -> matches
    # ------------------------------------------------------------------

    def scrape_and_store_results(self, offset: int = 0,
                                 force: bool = False,
                                 max_matches: Optional[int] = None,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None,
                                 event_name: Optional[str] = None,
                                 max_pages: int = 20,
                                 resume: bool = False) -> list[dict[str, Any]]:
        """Scrape results with pagination and optional event filter.

        Date filtering is applied at match detail level (see run_full_pipeline).

        Args:
            offset: Starting offset for results page.
            force: Whether to ignore disk cache.
            max_matches: Max matches to store (after filtering). None = all.
            start_date: Only store matches on or after this date (YYYY-MM-DD).
            end_date: Only store matches on or before this date (YYYY-MM-DD).
            event_name: Only store matches from this event (exact substring match).
            max_pages: Max result pages to scrape (50 matches per page). Default 20.
        """
        stored = []
        current_offset = offset

        if resume:
            progress = self._load_progress()
            if progress["last_offset"] > current_offset:
                current_offset = progress["last_offset"]
                logger.info("Resuming from saved offset %d", current_offset)

        for page in range(max_pages):
            matches = scrape_results_page(self._client, offset=current_offset, force=force)
            if not matches:
                logger.info("No more results at offset %d, stopping pagination", current_offset)
                break

            # Apply filters
            for m in matches:
                # Event name filter (only filter available at results page level)
                if event_name:
                    me_name = m.get("event_name") or ""
                    if event_name.lower() not in me_name.lower():
                        continue

                stored.append(m)

            # Stop if max_matches already hit
            if max_matches is not None and len(stored) >= max_matches:
                stored = stored[:max_matches]
                break

            logger.info("Page %d: fetched %d matches, %d stored so far",
                        page + 1, len(matches), len(stored))
            current_offset += 50

        # Persist to database
        # Pre-resolve event_name -> event_id lookup for event matching
        event_id_cache: dict[str, int] = {}
        for m in stored:
            team1_id = self._lookup_team_id_by_name(m.get("team1_name"))
            team2_id = self._lookup_team_id_by_name(m.get("team2_name"))
            winner = m.get("winner_team_id")
            if winner == 1:
                winner_id = team1_id
            elif winner == 2:
                winner_id = team2_id
            else:
                winner_id = None
            # Resolve event_id from event_name if not directly available
            me_id = m.get("event_id")
            me_name = m.get("event_name") or ""
            if me_id is None and me_name:
                if me_name not in event_id_cache:
                    rows = self._db.execute(
                        "SELECT event_id FROM events WHERE event_name LIKE ?",
                        (me_name,)
                    )
                    if rows:
                        event_id_cache[me_name] = rows[0]["event_id"]
                cached = event_id_cache.get(me_name)
                if cached is not None:
                    me_id = cached

            try:
                self._db.upsert_match(
                    match_id=m["match_id"],
                    event_id=me_id,
                    event_name=me_name,
                    team1_id=team1_id,
                    team2_id=team2_id,
                    team1_score=m.get("team1_score"),
                    team2_score=m.get("team2_score"),
                    best_of=m.get("best_of"),
                    winner_team_id=winner_id,
                )
            except Exception as exc:
                logger.warning("Failed to upsert match %d: %s", m["match_id"], exc)
        logger.info("Upserted %d matches from %d pages (filtered)", len(stored), page + 1)
        return stored

    def _lookup_team_id_by_name(self, name: Optional[str]) -> Optional[int]:
        """Look up a team ID by name from the DB."""
        if not name:
            return None
        rows = self._db.execute(
            "SELECT team_id FROM teams WHERE team_name = ?", (name,)
        )
        return rows[0]["team_id"] if rows else None

    # ------------------------------------------------------------------
    # Match detail -> maps + player stats
    # ------------------------------------------------------------------

    def scrape_and_store_match_detail(self, match_id: int,
                                      match_path: str = "",
                                      force: bool = False) -> dict[str, Any]:
        detail = scrape_match_detail(self._client, match_id, match_path=match_path, force=force)

        # Persist match_datetime from detail page if available
        dt = detail.get("match_datetime")
        if dt:
            self._db._conn.execute(
                "UPDATE matches SET match_datetime = ? WHERE match_id = ?",
                (dt, match_id)
            )
            self._db._conn.commit()

        # Look up team IDs from match for FK mappings
        match_row = self._db.get_match(match_id)
        team1_id = match_row["team1_id"] if match_row else None
        team2_id = match_row["team2_id"] if match_row else None

        for i, mp in enumerate(detail.get("maps", []), start=1):
            map_id = match_id * 100 + i
            # Map winner_team_id from position (1/2) to actual team_id
            mp_winner = mp.get("winner_team_id")
            if mp_winner == 1:
                mapped_winner = team1_id
            elif mp_winner == 2:
                mapped_winner = team2_id
            else:
                mapped_winner = None
            self._db.upsert_map(
                map_id=map_id,
                match_id=match_id,
                map_name=mp["map_name"],
                team1_rounds=mp.get("team1_rounds"),
                team2_rounds=mp.get("team2_rounds"),
                winner_team_id=mapped_winner,
            )

        for i, ps in enumerate(detail.get("players", []), start=1):
            stat_id = match_id * 10000 + i
            try:
                self._db.upsert_player_match_stats(
                    id=stat_id,
                    match_id=match_id,
                    map_id=None,
                    player_id=ps.get("player_id"),
                    team_id=team1_id if ps.get("team_id") == 1 else team2_id,
                    rating=ps.get("rating"),
                    adr=ps.get("adr"),
                    swing=ps.get("swing"),
                    kast=ps.get("kast"),
                    kd_diff=ps.get("kd_diff"),
                    kills=ps.get("kills"),
                    deaths=ps.get("deaths"),
                )
            except Exception as exc:
                logger.warning("Failed to store stat %d: %s", stat_id, exc)

        logger.info(
            "Stored %d maps and %d player stats for match %d",
            len(detail.get("maps", [])),
            len(detail.get("players", [])),
            match_id,
        )
        return detail

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def scrape_and_store_all_ranking_players(self,
                                                   force: bool = False) -> int:
        """Extract all player rosters from the /ranking/teams page in one call.

        This replaces the per-team detail page scraping which often returns 404.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            players = scrape_ranking_players(self._client, force=force)
        except Exception as exc:
            logger.warning("Failed to fetch ranking players: %s", exc)
            return 0
        for p in players:
            self._db.upsert_player(
                player_id=p["player_id"],
                player_name=p["player_name"],
                nickname=p.get("nickname"),
                team_id=p.get("team_id"),
                updated_at=now,
            )
        logger.info("Upserted %d players from ranking page", len(players))
        return len(players)


    # ------------------------------------------------------------------
    # Name resolution helpers
    # ------------------------------------------------------------------

    def _resolve_event_by_name(self, event_name: str) -> Optional[int]:
        rows = self._db.execute(
            "SELECT event_id FROM events WHERE event_name LIKE ?",
            (f"%{event_name}%",)
        )
        if rows:
            if len(rows) > 1:
                logger.info("Multiple events match '%s', picking first", event_name)
            return rows[0]["event_id"]
        self.scrape_and_store_events(force=False)
        rows = self._db.execute(
            "SELECT event_id FROM events WHERE event_name LIKE ?",
            (f"%{event_name}%",)
        )
        if rows:
            return rows[0]["event_id"]
        return None

    def _resolve_team_by_name(self, team_name: str) -> Optional[int]:
        rows = self._db.execute(
            "SELECT team_id FROM teams WHERE team_name LIKE ?",
            (f"%{team_name}%",)
        )
        if rows:
            return rows[0]["team_id"]
        self.scrape_and_store_team_rankings(force=False)
        rows = self._db.execute(
            "SELECT team_id FROM teams WHERE team_name LIKE ?",
            (f"%{team_name}%",)
        )
        if rows:
            return rows[0]["team_id"]
        return None

    def _resolve_player_by_name(self, player_name: str) -> Optional[int]:
        rows = self._db.execute(
            "SELECT player_id FROM players WHERE player_name LIKE ? OR nickname LIKE ?",
            (f"%{player_name}%", f"%{player_name}%")
        )
        if rows:
            return rows[0]["player_id"]
        self.scrape_and_store_all_ranking_players(force=False)
        rows = self._db.execute(
            "SELECT player_id FROM players WHERE player_name LIKE ? OR nickname LIKE ?",
            (f"%{player_name}%", f"%{player_name}%")
        )
        if rows:
            return rows[0]["player_id"]
        return None


    # ------------------------------------------------------------------
    # Targeted scraping: event / team / player
    # ------------------------------------------------------------------

    def _scrape_and_store_matches(self, match_entries: list[dict[str, Any]],
                                   force: bool = False) -> dict[str, int]:
        counts = {'matches_found': len(match_entries), 'detail_scraped': 0, 'maps': 0, 'player_stats': 0}
        for m in match_entries:
            try:
                detail = self.scrape_and_store_match_detail(
                    m['match_id'], match_path=m.get('match_url', ''), force=force,
                )
                counts['maps'] += len(detail.get('maps', []))
                counts['player_stats'] += len(detail.get('players', []))
                counts['detail_scraped'] += 1
            except Exception as exc:
                logger.warning('Failed to scrape match %%d: %%s', m['match_id'], exc)
        return counts

    def scrape_event_by_id(self, event_id: int, force: bool = False,
                            max_matches: int | None = None) -> dict[str, int]:
        ev = self._db.get_event(event_id)
        if not ev:
            self.scrape_and_store_events(force=force)
            ev = self._db.get_event(event_id)
        if ev:
            logger.info('Target event: %%s (ID=%%d)', ev['event_name'], event_id)
        else:
            logger.info('Scraping event ID=%%d', event_id)

        matches = scrape_event_matches(self._client, event_id, force=force)
        logger.info('Found %%d matches for event %%d', len(matches), event_id)

        detail_matches = matches[:max_matches] if max_matches is not None else matches
        return self._scrape_and_store_matches(detail_matches, force=force)

    def scrape_team_at_event(self, team_id: int, event_id: int,
                              force: bool = False) -> dict[str, int]:
        team = self._db.get_team(team_id)
        team_name = team['team_name'] if team else str(team_id)
        if not team:
            self.scrape_and_store_team_rankings(force=force)
            team = self._db.get_team(team_id)
            team_name = team['team_name'] if team else str(team_id)

        logger.info('Target: team "%%s" (ID=%%d) at event %%d', team_name, team_id, event_id)

        matches = scrape_event_matches(self._client, event_id, force=force)
        logger.info('Found %%d matches for event %%d, checking for team %%s',
                    len(matches), event_id, team_name)

        counts = {'matches_found': len(matches), 'detail_scraped': 0,
                  'team_matches': 0, 'maps': 0, 'player_stats': 0}
        for m in matches:
            try:
                detail = self.scrape_and_store_match_detail(
                    m['match_id'], match_path=m.get('match_url', ''), force=force,
                )
                counts['maps'] += len(detail.get('maps', []))
                counts['player_stats'] += len(detail.get('players', []))
                counts['detail_scraped'] += 1

                match_row = self._db.get_match(m['match_id'])
                if match_row and (match_row['team1_id'] == team_id
                                  or match_row['team2_id'] == team_id):
                    counts['team_matches'] += 1
            except Exception as exc:
                logger.warning('Failed to scrape match %%d: %%s', m['match_id'], exc)

        logger.info('Team %%s played %%d matches at event %%d',
                    team_name, counts['team_matches'], event_id)
        return counts

    def scrape_player_at_event(self, player_id: int, event_id: int,
                                force: bool = False) -> dict[str, int]:
        player = self._db.get_player(player_id)
        player_name = player['player_name'] if player else str(player_id)
        if not player:
            self.scrape_and_store_all_ranking_players(force=force)
            player = self._db.get_player(player_id)
            player_name = player['player_name'] if player else str(player_id)

        logger.info('Target: player "%%s" (ID=%%d) at event %%d',
                    player_name, player_id, event_id)

        matches = scrape_event_matches(self._client, event_id, force=force)
        logger.info('Found %%d matches for event %%d, checking for player %%s',
                    len(matches), event_id, player_name)

        counts = {'matches_found': len(matches), 'detail_scraped': 0,
                  'player_matches': 0, 'maps': 0, 'player_stats': 0}
        for m in matches:
            try:
                detail = self.scrape_and_store_match_detail(
                    m['match_id'], match_path=m.get('match_url', ''), force=force,
                )
                counts['maps'] += len(detail.get('maps', []))
                counts['player_stats'] += len(detail.get('players', []))
                counts['detail_scraped'] += 1

                stats = self._db.get_stats_by_match(m['match_id'])
                for stat in stats:
                    if stat.get('player_id') == player_id:
                        counts['player_matches'] += 1
                        break
            except Exception as exc:
                logger.warning('Failed to scrape match %%d: %%s', m['match_id'], exc)

        logger.info('Player %%s played %%d matches at event %%d',
                    player_name, counts['player_matches'], event_id)
        return counts

    def run_full_pipeline(self, force: bool = False,
                          max_matches: Optional[int] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          event_name: Optional[str] = None,
                          max_pages: int = 20,
                          resume: bool = False) -> dict[str, int]:
        """Run the complete scraping pipeline end-to-end.

        Args:
            force: Whether to force re-scraping (ignore disk cache).
            max_matches: Maximum number of match details to scrape.
                         None means all available matches.
            start_date: Only scrape matches on or after this date (YYYY-MM-DD).
            end_date: Only scrape matches on or before this date (YYYY-MM-DD).
            event_name: Only scrape matches from this event (substring match).
            max_pages: Max result pages to scrape (50 matches per page).

        Returns counts of scraped items per category.
        """
        counts: dict[str, int] = {}

        # Load or init progress
        progress = self._load_progress() if resume else {"last_offset": 0, "scraped_match_ids": [], "failed_match_ids": []}
        scraped_set: set[int] = set(progress.get("scraped_match_ids", []))
        failed_set: set[int] = set(progress.get("failed_match_ids", []))

        if not resume:
            counts["events"] = self.scrape_and_store_events(force=force)
            counts["team_rankings"] = self.scrape_and_store_team_rankings(force=force)

            player_count = self.scrape_and_store_all_ranking_players(
                force=force
            )
            counts["players"] = player_count

        matches = self.scrape_and_store_results(
            offset=0, force=force,
            start_date=start_date,
            end_date=end_date,
            event_name=event_name,
            max_pages=max_pages,
            resume=resume,
        )
        map_count = 0
        stat_count = 0
        total_detail = 0
        # Filter matches by date range (requires match_detail to have datetime)
        # For results without datetime, they will be included and datetime resolved during detail scrape
        detail_matches = matches[:max_matches] if max_matches is not None else matches

        for m in detail_matches:
            mid = m["match_id"]
            if mid in scraped_set:
                continue
            if mid in failed_set:
                continue
            try:
                detail = self.scrape_and_store_match_detail(
                    mid,
                    match_path=m.get("match_url", ""),
                    force=force,
                )

                # Check date range filter using resolved match_datetime
                if start_date or end_date:
                    dt = detail.get("match_datetime") or ""
                    match_date = dt[:10]
                    if start_date and match_date < start_date:
                        logger.debug("Skipping match %d (before %s)", mid, start_date)
                        scraped_set.add(mid)
                        total_detail += 1
                        continue
                    if end_date and match_date > end_date:
                        logger.debug("Skipping match %d (after %s)", mid, end_date)
                        scraped_set.add(mid)
                        total_detail += 1
                        continue

                map_count += len(detail.get("maps", []))
                stat_count += len(detail.get("players", []))
                scraped_set.add(mid)
                total_detail += 1
            except Exception as exc:
                logger.warning("Failed to scrape match %d: %s", mid, exc)
                failed_set.add(mid)

            # Save progress every 10 matches
            if total_detail % 10 == 0:
                progress["scraped_match_ids"] = list(scraped_set)
                progress["failed_match_ids"] = list(failed_set)
                self._save_progress(progress)

        # Final save
        progress["scraped_match_ids"] = list(scraped_set)
        progress["failed_match_ids"] = list(failed_set)
        if resume and matches:
            progress["last_offset"] = progress.get("last_offset", 0) + 50 * len(matches)  # approximate
        self._save_progress(progress) if resume else None

        counts["maps"] = map_count
        counts["player_stats"] = stat_count
        counts["detail_scraped"] = total_detail
        if not resume:
            logger.info("Run complete — %s", counts)
        else:
            logger.info("Resume run complete — %s", counts)

        return counts

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.close()
