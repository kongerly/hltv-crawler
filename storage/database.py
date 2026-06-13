"""Database manager — high-level CRUD for all six tables."""

import sqlite3
from pathlib import Path
from typing import Any, Optional

from storage.schema import create_tables as _create_tables, migrate_schema as _migrate_schema


class Database:
    """Wraps a SQLite connection and provides CRUD helpers."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._conn: sqlite3.Connection = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")

    # -----------------------------------------------------------------------
    # Schema
    # -----------------------------------------------------------------------

    def create_tables(self) -> None:
        """Create all tables if they do not exist and run migrations."""
        _create_tables(self._conn)
        _migrate_schema(self._conn)

    # -----------------------------------------------------------------------
    # Teams
    # -----------------------------------------------------------------------

    def upsert_team(self, team_id: int, team_name: str,
                    world_rank: Optional[int] = None,
                    updated_at: Optional[str] = None) -> None:
        self._conn.execute(
            """INSERT INTO teams (team_id, team_name, world_rank, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(team_id) DO UPDATE SET
                   team_name  = excluded.team_name,
                   world_rank = excluded.world_rank,
                   updated_at = excluded.updated_at""",
            (team_id, team_name, world_rank, updated_at),
        )
        self._conn.commit()

    def get_team(self, team_id: int) -> Optional[dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM teams WHERE team_id = ?", (team_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_teams(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM teams")]

    # -----------------------------------------------------------------------
    # Players
    # -----------------------------------------------------------------------

    def upsert_player(self, player_id: int, player_name: str,
                      nickname: Optional[str] = None,
                      team_id: Optional[int] = None,
                      updated_at: Optional[str] = None) -> None:
        self._conn.execute(
            """INSERT INTO players (player_id, player_name, nickname, team_id, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(player_id) DO UPDATE SET
                   player_name = excluded.player_name,
                   nickname    = excluded.nickname,
                   team_id     = excluded.team_id,
                   updated_at  = excluded.updated_at""",
            (player_id, player_name, nickname, team_id, updated_at),
        )
        self._conn.commit()

    def get_player(self, player_id: int) -> Optional[dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM players WHERE player_id = ?", (player_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_players_by_team(self, team_id: int) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._conn.execute(
                "SELECT * FROM players WHERE team_id = ?", (team_id,)
            )
        ]

    # -----------------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------------

    def upsert_event(self, event_id: int, event_name: str,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> None:
        self._conn.execute(
            """INSERT INTO events (event_id, event_name, start_date, end_date)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(event_id) DO UPDATE SET
                   event_name = excluded.event_name,
                   start_date = excluded.start_date,
                   end_date   = excluded.end_date""",
            (event_id, event_name, start_date, end_date),
        )
        self._conn.commit()

    def get_event(self, event_id: int) -> Optional[dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_events(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM events")]

    # -----------------------------------------------------------------------
    # Matches
    # -----------------------------------------------------------------------

    def upsert_match(self, match_id: int, event_id: Optional[int],
                  event_name: Optional[str] = None,
                  match_datetime: Optional[str] = None,
                  team1_id: Optional[int] = None,
                  team2_id: Optional[int] = None,
                  team1_score: Optional[int] = None,
                  team2_score: Optional[int] = None,
                  best_of: Optional[int] = None,
                  winner_team_id: Optional[int] = None) -> None:
        self._conn.execute(
            """INSERT INTO matches
               (match_id, event_id, event_name, match_datetime,
                team1_id, team2_id, team1_score, team2_score,
                best_of, winner_team_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(match_id) DO UPDATE SET
                   event_id       = excluded.event_id,
                   event_name     = excluded.event_name,
                   match_datetime = excluded.match_datetime,
                   team1_id       = excluded.team1_id,
                   team2_id       = excluded.team2_id,
                   team1_score    = excluded.team1_score,
                   team2_score    = excluded.team2_score,
                   best_of        = excluded.best_of,
                   winner_team_id = excluded.winner_team_id""",
            (match_id, event_id, event_name, match_datetime,
             team1_id, team2_id, team1_score, team2_score,
             best_of, winner_team_id),
        )
        self._conn.commit()
    def get_match(self, match_id: int) -> Optional[dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_matches_by_event(self, event_id: int) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._conn.execute(
                "SELECT * FROM matches WHERE event_id = ?", (event_id,)
            )
        ]

    def get_matches_by_date_range(self,
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None,
                                   event_id: Optional[int] = None
                                   ) -> list[dict[str, Any]]:
        """Get matches filtered by date range and optionally by event."""
        conditions: list[str] = []
        params: list[Any] = []
        if start_date:
            conditions.append("match_datetime >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("match_datetime <= ?")
            params.append(end_date)
        if event_id is not None:
            conditions.append("event_id = ?")
            params.append(event_id)
        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM matches WHERE {where} ORDER BY match_datetime DESC"
        return [
            dict(r)
            for r in self._conn.execute(sql, params)
        ]

    def get_maps_by_match_with_side(self, match_id: int) -> list[dict[str, Any]]:
        """Get maps for a match, extracting CT/T rounds from detail."""
        return [
            dict(r)
            for r in self._conn.execute(
                "SELECT * FROM maps WHERE match_id = ?", (match_id,)
            )
        ]

    # -----------------------------------------------------------------------
    # Maps
    # -----------------------------------------------------------------------

    def upsert_map(self, map_id: int, match_id: int, map_name: str,
                   team1_rounds: Optional[int] = None,
                   team2_rounds: Optional[int] = None,
                   team1_ct_rounds: Optional[int] = None,
                   team1_t_rounds: Optional[int] = None,
                   team2_ct_rounds: Optional[int] = None,
                   team2_t_rounds: Optional[int] = None,
                   winner_team_id: Optional[int] = None) -> None:
        self._conn.execute(
            """INSERT INTO maps
               (map_id, match_id, map_name,
                team1_rounds, team2_rounds,
                team1_ct_rounds, team1_t_rounds,
                team2_ct_rounds, team2_t_rounds,
                winner_team_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(map_id) DO UPDATE SET
                   match_id       = excluded.match_id,
                   map_name       = excluded.map_name,
                   team1_rounds   = excluded.team1_rounds,
                   team2_rounds   = excluded.team2_rounds,
                   team1_ct_rounds = excluded.team1_ct_rounds,
                   team1_t_rounds  = excluded.team1_t_rounds,
                   team2_ct_rounds = excluded.team2_ct_rounds,
                   team2_t_rounds  = excluded.team2_t_rounds,
                   winner_team_id = excluded.winner_team_id""",
            (map_id, match_id, map_name,
             team1_rounds, team2_rounds,
             team1_ct_rounds, team1_t_rounds,
             team2_ct_rounds, team2_t_rounds,
             winner_team_id),
        )
        self._conn.commit()

    def get_maps_by_match(self, match_id: int) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._conn.execute(
                "SELECT * FROM maps WHERE match_id = ?", (match_id,)
            )
        ]

    # -----------------------------------------------------------------------
    # Player Match Stats
    # -----------------------------------------------------------------------

    def upsert_player_match_stats(self, id: int, match_id: int,
                                   map_id: Optional[int] = None,
                                   player_id: Optional[int] = None,
                                   team_id: Optional[int] = None,
                                   rating: Optional[float] = None,
                                   adr: Optional[float] = None,
                                   swing: Optional[float] = None,
                                   kast: Optional[float] = None,
                                   kd_diff: Optional[int] = None,
                                   kills: Optional[int] = None,
                                   deaths: Optional[int] = None) -> None:
        # Use -1 for missing player_id to avoid FK constraint failure
        actual_player_id = player_id if player_id is not None else -1
        # Ensure player row exists FIRST (for FK constraint)
        self._conn.execute(
            "INSERT OR IGNORE INTO players (player_id, player_name, nickname) VALUES (?, ?, ?)",
            (actual_player_id, 'Player_{}'.format(actual_player_id) if actual_player_id == -1 else 'Unknown Player', None),
        )
        self._conn.execute(
            """INSERT INTO player_match_stats
               (id, match_id, map_id, player_id, team_id,
                rating, adr, swing, kast, kd_diff, kills, deaths)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   match_id   = excluded.match_id,
                   map_id     = excluded.map_id,
                   player_id  = excluded.player_id,
                   team_id    = excluded.team_id,
                   rating     = excluded.rating,
                   adr        = excluded.adr,
                   swing      = excluded.swing,
                   kast       = excluded.kast,
                   kd_diff    = excluded.kd_diff,
                   kills      = excluded.kills,
                   deaths     = excluded.deaths""",
            (id, match_id, map_id, actual_player_id, team_id,
             rating, adr, swing, kast, kd_diff, kills, deaths),
        )
        self._conn.commit()

    def get_stats_by_match(self, match_id: int) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._conn.execute(
                "SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,)
            )
        ]

    def get_stats_by_player(self, player_id: int) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._conn.execute(
                "SELECT * FROM player_match_stats WHERE player_id = ?", (player_id,)
            )
        ]

    # -----------------------------------------------------------------------
    # Generic helpers
    # -----------------------------------------------------------------------

    def execute(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute arbitrary SQL and return results as dicts."""
        return [dict(r) for r in self._conn.execute(sql, params)]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.close()
