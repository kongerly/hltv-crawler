"""SQLite schema DDL, table creation, and migration helpers.

Defines the six core tables for HLTV CS2 data, plus schema migrations
teams, players, events, matches, maps, player_match_stats.
"""

import sqlite3

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

CREATE_TEAMS = """
CREATE TABLE IF NOT EXISTS teams (
    team_id    INTEGER PRIMARY KEY,
    team_name  TEXT    NOT NULL,
    world_rank INTEGER,
    updated_at TEXT    -- ISO 8601
);
"""

CREATE_PLAYERS = """
CREATE TABLE IF NOT EXISTS players (
    player_id   INTEGER PRIMARY KEY,
    player_name TEXT    NOT NULL,
    nickname    TEXT,               -- in-game handle
    team_id     INTEGER REFERENCES teams(team_id),
    updated_at  TEXT                -- ISO 8601
);
"""

CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    event_id   INTEGER PRIMARY KEY,
    event_name TEXT    NOT NULL,
    start_date TEXT,                -- ISO 8601
    end_date   TEXT                 -- ISO 8601
);
"""

CREATE_MATCHES = """
CREATE TABLE IF NOT EXISTS matches (
    match_id        INTEGER PRIMARY KEY,
    event_id        INTEGER REFERENCES events(event_id),
    event_name      TEXT,           -- denormalised from events table
    match_datetime  TEXT,           -- ISO 8601
    team1_id        INTEGER REFERENCES teams(team_id),
    team2_id        INTEGER REFERENCES teams(team_id),
    team1_score     INTEGER,
    team2_score     INTEGER,
    best_of         INTEGER,        -- e.g. 3 for Bo3
    winner_team_id  INTEGER REFERENCES teams(team_id)
);
"""

CREATE_MAPS = """
CREATE TABLE IF NOT EXISTS maps (
    map_id          INTEGER PRIMARY KEY,
    match_id        INTEGER REFERENCES matches(match_id),
    map_name        TEXT    NOT NULL,
    team1_rounds    INTEGER,
    team2_rounds    INTEGER,
    team1_ct_rounds INTEGER,
    team1_t_rounds  INTEGER,
    team2_ct_rounds INTEGER,
    team2_t_rounds  INTEGER,
    winner_team_id  INTEGER REFERENCES teams(team_id)
);
"""

CREATE_PLAYER_MATCH_STATS = """
CREATE TABLE IF NOT EXISTS player_match_stats (
    id         INTEGER PRIMARY KEY,
    match_id   INTEGER REFERENCES matches(match_id),
    map_id     INTEGER REFERENCES maps(map_id),
    player_id  INTEGER REFERENCES players(player_id),
    team_id    INTEGER REFERENCES teams(team_id),
    rating     REAL,
    adr        REAL,
    kast       REAL,
    swing      REAL,
    kd_diff    INTEGER,
    kills      INTEGER,
    deaths     INTEGER
);
"""

ALL_DDL = [
    CREATE_TEAMS,
    CREATE_PLAYERS,
    CREATE_EVENTS,
    CREATE_MATCHES,
    CREATE_MAPS,
    CREATE_PLAYER_MATCH_STATS,
]


def create_tables(conn: sqlite3.Connection) -> None:
    """Execute all CREATE TABLE statements inside a single transaction."""
    for ddl in ALL_DDL:
        conn.execute(ddl)
    conn.commit()


# ---------------------------------------------------------------------------
# Schema migration helpers
# ---------------------------------------------------------------------------


_MIGRATIONS_V2 = [
    "ALTER TABLE matches ADD COLUMN event_name TEXT",
    "ALTER TABLE maps ADD COLUMN team1_ct_rounds INTEGER",
    "ALTER TABLE maps ADD COLUMN team1_t_rounds INTEGER",
    "ALTER TABLE maps ADD COLUMN team2_ct_rounds INTEGER",
    "ALTER TABLE maps ADD COLUMN team2_t_rounds INTEGER",
]


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return current schema version from pragma or 0 for fresh DB."""
    row = conn.execute("PRAGMA user_version").fetchone()
    return row[0] if row else 0


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Run non-destructive migrations to bring existing DB to latest version."""
    version = get_schema_version(conn)
    if version >= 2:
        return
    for ddl in _MIGRATIONS_V2:
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass
    conn.execute("PRAGMA user_version = 2")
    conn.commit()
