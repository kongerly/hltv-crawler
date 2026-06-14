"""Scrape event listings from HLTV."""

from typing import Any

from scraper.http_client import HltvHttpClient
from parser import parse_events_page, parse_event_match_list


def scrape_events(client: HltvHttpClient, force: bool = False) -> list[dict[str, Any]]:
    """Scrape the /events page and return parsed event data."""
    html = client.get("/events", force=force)
    return parse_events_page(html)

def scrape_event_matches(client: 'HltvHttpClient', event_id: int, force: bool = False) -> list[dict[str, Any]]:
    """Scrape event detail page for list of matches belonging to this event."""
    html = client.get(f"/events/{event_id}/", force=force)
    return parse_event_match_list(html, event_id)

