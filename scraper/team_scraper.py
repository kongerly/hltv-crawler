"""Scrape team and player data from HLTV."""

from typing import Any

from parser import parse_ranking_players, parse_team_ranking_page
from scraper.http_client import HltvHttpClient


def scrape_team_rankings(
    client: HltvHttpClient, force: bool = False
) -> list[dict[str, Any]]:
    """Scrape the /ranking/teams page.

    Returns list of dicts: team_id, team_name, world_rank.
    """
    html = client.get("/ranking/teams", force=force)
    return parse_team_ranking_page(html)


def scrape_team_detail(
    client: HltvHttpClient, team_id: int, force: bool = False
) -> list[dict[str, Any]]:
    """Scrape a single team roster from the ranking page.

    Returns list of dicts: player_id, player_name, nickname, team_id.
    """
    html = client.get("/ranking/teams", force=force)
    players = parse_ranking_players(html)
    return [player for player in players if player["team_id"] == team_id]


def scrape_ranking_players(
    client: HltvHttpClient, force: bool = False
) -> list[dict[str, Any]]:
    """Scrape the /ranking/teams page for player rosters.

    Returns list of dicts: player_id, player_name, nickname, team_id.
    This replaces the individual team detail page scraping (which 404s for many teams).
    """
    html = client.get("/ranking/teams", force=force)
    return parse_ranking_players(html)
