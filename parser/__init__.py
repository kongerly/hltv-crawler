"""HLTV Data Parsers — extract structured data from HTML pages."""

from parser.parsers import (
    parse_events_page,
    parse_results_page,
    parse_match_detail,
    parse_team_ranking_page,
    parse_ranking_players,
)

__all__ = [
    "parse_events_page",
    "parse_results_page",
    "parse_match_detail",
    "parse_team_ranking_page",
    "parse_ranking_players",
]
