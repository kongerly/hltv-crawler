"""Tests for the storage layer — database CRUD operations."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from storage.database import Database

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Generator[Database, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        with Database(path) as database:
            database.create_tables()
            yield database


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


class TestTeams:
    def test_upsert_and_get_team(self, db: Database):
        db.upsert_team(team_id=1, team_name="FaZe", world_rank=1)
        row = db.get_team(1)
        assert row is not None
        assert row["team_name"] == "FaZe"
        assert row["world_rank"] == 1

    def test_upsert_updates_existing_team(self, db: Database):
        db.upsert_team(team_id=1, team_name="FaZe", world_rank=1)
        db.upsert_team(team_id=1, team_name="FaZe Clan", world_rank=2)
        row = db.get_team(1)
        assert row["team_name"] == "FaZe Clan"
        assert row["world_rank"] == 2

    def test_get_team_not_found(self, db: Database):
        assert db.get_team(999) is None

    def test_get_all_teams(self, db: Database):
        db.upsert_team(1, "FaZe")
        db.upsert_team(2, "NaVi")
        teams = db.get_all_teams()
        assert len(teams) == 2

    def test_upsert_team_with_optional_fields(self, db: Database):
        db.upsert_team(team_id=3, team_name="G2", world_rank=5)
        row = db.get_team(3)
        assert row["world_rank"] == 5


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


class TestPlayers:
    def test_upsert_and_get_player(self, db: Database):
        db.upsert_team(1, "FaZe")
        db.upsert_player(player_id=10, player_name="ropz", team_id=1)
        row = db.get_player(10)
        assert row is not None
        assert row["player_name"] == "ropz"

    def test_upsert_player_with_team_ref(self, db: Database):
        db.upsert_team(1, "FaZe")
        db.upsert_player(player_id=10, player_name="ropz", team_id=1)
        row = db.execute("SELECT * FROM players WHERE player_id = ?", [10])
        assert len(row) == 1
        assert row[0]["team_id"] == 1

    def test_get_player_not_found(self, db: Database):
        assert db.get_player(999) is None


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class TestEvents:
    def test_upsert_and_get_event(self, db: Database):
        db.upsert_event(event_id=1, event_name="IEM Katowice")
        row = db.get_event(1)
        assert row is not None
        assert row["event_name"] == "IEM Katowice"

    def test_upsert_event_with_dates(self, db: Database):
        db.upsert_event(
            event_id=2,
            event_name="ESL Pro League",
            start_date="2025-03-01",
            end_date="2025-04-01",
        )
        row = db.get_event(2)
        assert row["start_date"] == "2025-03-01"


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------


class TestMatches:
    def test_upsert_and_get_match(self, db: Database):
        db.upsert_team(1, "FaZe")
        db.upsert_team(2, "NaVi")
        db.upsert_event(event_id=1, event_name="Test Event")
        db.upsert_match(
            match_id=100,
            event_id=1,
            team1_id=1,
            team2_id=2,
            team1_score=13,
            team2_score=7,
            best_of=3,
            winner_team_id=1,
        )
        row = db.get_match(100)
        assert row is not None
        assert row["team1_score"] == 13
        assert row["team2_score"] == 7

    def test_get_match_not_found(self, db: Database):
        assert db.get_match(999) is None


# ---------------------------------------------------------------------------
# Maps
# ---------------------------------------------------------------------------


class TestMaps:
    def test_upsert_and_get_maps(self, db: Database):
        db.upsert_team(1, "FaZe")
        db.upsert_team(2, "NaVi")
        db.upsert_event(event_id=1, event_name="Test Event")
        db.upsert_match(match_id=100, event_id=1, team1_id=1, team2_id=2)
        db.upsert_map(
            map_id=1,
            match_id=100,
            map_name="Mirage",
            team1_rounds=13,
            team2_rounds=7,
            winner_team_id=1,
        )
        maps = db.get_maps_by_match(100)
        assert len(maps) == 1
        assert maps[0]["map_name"] == "Mirage"

    def test_get_maps_empty(self, db: Database):
        assert db.get_maps_by_match(999) == []


# ---------------------------------------------------------------------------
# Player Match Stats
# ---------------------------------------------------------------------------


class TestPlayerMatchStats:
    def test_upsert_and_get_stats(self, db: Database):
        db.upsert_team(1, "FaZe")
        db.upsert_team(2, "NaVi")
        db.upsert_event(event_id=1, event_name="Test Event")
        db.upsert_match(match_id=100, event_id=1, team1_id=1, team2_id=2)
        db.upsert_player(player_id=10, player_name="ropz", team_id=1)
        db.upsert_player_match_stats(
            id=1,
            match_id=100,
            player_id=10,
            team_id=1,
            rating=1.25,
            adr=95.3,
            kast=78.5,
            kills=22,
            deaths=15,
        )
        stats = db.get_stats_by_match(match_id=100)
        assert len(stats) == 1
        assert stats[0]["rating"] == 1.25


# ---------------------------------------------------------------------------
# Maps with CT/T side rounds
# ---------------------------------------------------------------------------


class TestMapsWithSide:
    def test_upsert_map_with_ct_t_rounds(self, db: Database):
        db.upsert_team(1, "FaZe")
        db.upsert_team(2, "NaVi")
        db.upsert_event(event_id=1, event_name="Test Event")
        db.upsert_match(match_id=100, event_id=1, team1_id=1, team2_id=2)
        db.upsert_map(
            map_id=1,
            match_id=100,
            map_name="Nuke",
            team1_rounds=13,
            team2_rounds=7,
            team1_ct_rounds=6,
            team1_t_rounds=7,
            team2_ct_rounds=5,
            team2_t_rounds=2,
            winner_team_id=1,
        )
        maps = db.get_maps_by_match(100)
        assert maps[0]["team1_ct_rounds"] == 6
        assert maps[0]["team2_t_rounds"] == 2


# ---------------------------------------------------------------------------
# Execute helper
# ---------------------------------------------------------------------------


class TestExecute:
    def test_execute_returns_dicts(self, db: Database):
        rows = db.execute("SELECT 1 as val")
        assert rows == [{"val": 1}]

    def test_execute_with_params(self, db: Database):
        db.upsert_team(1, "FaZe")
        rows = db.execute("SELECT * FROM teams WHERE team_id = ?", [1])
        assert len(rows) == 1
