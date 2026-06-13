"""Scrape match data from HLTV — results list and match details."""

from typing import Any

from scraper.http_client import HltvHttpClient
from parser import parse_match_detail, parse_results_page


def scrape_results_page(client: HltvHttpClient,
                         offset: int = 0,
                         force: bool = False) -> list[dict[str, Any]]:
    """Scrape the /results page with optional offset (pagination)."""
    path = f"/results" + (f"?offset={offset}" if offset else "")
    html = client.get(path, force=force)
    return parse_results_page(html)


def scrape_match_detail(client: HltvHttpClient,
                         match_id: int,
                         match_path: str = "", force: bool = False) -> dict[str, Any]:
    """Scrape a single match detail page.

    Returns dict with keys *maps* and *players*.
    """
    path = match_path or f"/matches/{match_id}/"
    html = client.get(path, force=force)
    return parse_match_detail(html)
