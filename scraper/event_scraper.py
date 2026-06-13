"""Scrape event listings from HLTV."""

from typing import Any

from scraper.http_client import HltvHttpClient
from parser import parse_events_page


def scrape_events(client: HltvHttpClient, force: bool = False) -> list[dict[str, Any]]:
    """Scrape the /events page and return parsed event data."""
    html = client.get("/events", force=force)
    return parse_events_page(html)
