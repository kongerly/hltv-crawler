"""HTML parsers — extract structured data from HLTV pages.

Based on actual HLTV HTML structure as of June 2026.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def parse_events_page(html: str) -> list[dict[str, Any]]:
    """Parse the /events page, return list of event dicts."""
    soup = BeautifulSoup(html, "html.parser")
    events: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for holder in soup.find_all("div", class_="ongoing-event-holder"):
        _parse_event(holder, seen_ids, events)

    events_holder = soup.find("div", class_="events-holder")
    if events_holder:
        for a in events_holder.find_all("a", href=lambda h: h and "/events/" in h):
            _parse_event(a, seen_ids, events)

    return events


def _parse_event(container_or_link, seen_ids, events):
    if container_or_link.name == "a":
        link = container_or_link
    else:
        link = container_or_link.find("a", href=re.compile(r"/events/(\d+)/"))
        if not link:
            return
    href = link.get("href", "")
    m = re.search(r"/events/(\d+)/", href)
    event_id = int(m.group(1)) if m else None
    if not event_id or event_id in seen_ids:
        return
    seen_ids.add(event_id)
    full_text = link.get_text(strip=True)
    event_name = full_text
    for sep in ["$", "|", "Teams", "Prize", "Players"]:
        idx = event_name.find(sep)
        if idx > 0:
            event_name = event_name[:idx].strip()
    date_text = ""
    date_match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(st|nd|rd|th)?", full_text)
    if date_match:
        s = date_match.start()
        date_text = full_text[s:].split("$")[0].split("Teams")[0].split("Prize")[0].strip()
    events.append({
        "event_id": event_id,
        "event_name": event_name,
        "start_date": date_text if date_text else None,
        "end_date": None,
    })
def parse_results_page(html: str) -> list[dict[str, Any]]:
    """Parse the /results page, return list of match dicts.

    Each match is inside div.result-con with a nested table:
      tr > td.team-cell (team1)
         > td.result-score (score1-score2)
         > td.team-cell (team2)
         > td.event > span.event-name
         > td.star-cell > div.map-text (bo3 etc)
    """
    soup = BeautifulSoup(html, "html.parser")
    matches: list[dict[str, Any]] = []

    result_rows = soup.find_all("div", class_="result-con")
    for row in result_rows:
        parsed = _parse_result_con(row)
        if parsed and parsed.get("match_id"):
            matches.append(parsed)

    return matches


def _parse_result_con(row: Tag) -> Optional[dict[str, Any]]:
    """Parse one div.result-con into a match dict."""
    try:
        a_tag = row.find("a", href=re.compile(r"/matches/(\d+)/"))
        if not a_tag:
            return None
        href = a_tag.get("href", "")
        m = re.search(r"/matches/(\d+)/", href)
        match_id = int(m.group(1)) if m else None

        team_cells = row.find_all("td", class_="team-cell")
        team1_div = team_cells[0].find("div", class_="team") if len(team_cells) > 0 else None
        team2_div = team_cells[1].find("div", class_="team") if len(team_cells) > 1 else None
        team1_name = team1_div.get_text(strip=True) if team1_div else None
        team2_name = team2_div.get_text(strip=True) if team2_div else None

        team1_won = team1_div and "team-won" in (team1_div.get("class") or [])
        team2_won = team2_div and "team-won" in (team2_div.get("class") or [])

        score_el = row.find("td", class_="result-score")
        score_text = score_el.get_text(strip=True) if score_el else ""
        team1_score = None
        team2_score = None
        if "-" in score_text:
            parts = score_text.split("-")
            try:
                team1_score = int(parts[0])
                team2_score = int(parts[1])
            except ValueError:
                pass

        event_el = row.find("td", class_="event")
        event_name = None
        if event_el:
            name_span = event_el.find("span", class_="event-name")
            if name_span:
                event_name = name_span.get_text(strip=True)

        map_text_el = row.find("div", class_="map-text")
        best_of = None
        if map_text_el:
            bo_match = re.search(r"bo(\d)", map_text_el.get_text(strip=True), re.IGNORECASE)
            if bo_match:
                best_of = int(bo_match.group(1))

        winner_team_id = None
        if team1_won:
            winner_team_id = 1
        elif team2_won:
            winner_team_id = 2

        return {
            "match_id": match_id,
            "match_url": href,
            "team1_name": team1_name,
            "team2_name": team2_name,
            "team1_score": team1_score,
            "team2_score": team2_score,
            "event_name": event_name,
            "match_datetime": None,
            "best_of": best_of,
            "winner_team_id": winner_team_id,
        }
    except (AttributeError, ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Match detail page (maps + player stats)
# ---------------------------------------------------------------------------

def parse_match_detail(html: str) -> dict[str, Any]:
    """Parse a match detail page for maps and player stats.

    Maps are extracted from div.mapholder (map name + team scores).
    CT/T side rounds are extracted from results-center-half-score spans.
    Player stats are extracted from table.totalstats blocks (overall only).
    Match datetime is extracted from div.date data-unix attribute.
    """
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, Any] = {"maps": [], "players": [], "match_datetime": None}

    # --- Match datetime from div.date data-unix ---
    date_div = soup.find("div", class_="date", attrs={"data-unix": True})
    if date_div:
        unix_ms = date_div.get("data-unix")
        if unix_ms:
            try:
                dt = datetime.fromtimestamp(int(unix_ms) / 1000, tz=timezone.utc)
                result["match_datetime"] = dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            except (ValueError, OSError):
                pass

    # --- Maps via div.mapholder ---
    for mh in soup.find_all("div", class_="mapholder"):
        map_name = None
        team1_rounds = None
        team2_rounds = None
        team1_ct_rounds = None
        team1_t_rounds = None
        team2_ct_rounds = None
        team2_t_rounds = None

        name_el = mh.find("div", class_="mapname")
        if name_el:
            map_name = name_el.get_text(strip=True)

        score_els = mh.select(".results-team-score")
        if len(score_els) >= 2:
            try:
                t1 = score_els[0].get_text(strip=True)
                t2 = score_els[1].get_text(strip=True)
                if t1 != "-":
                    team1_rounds = int(t1)
                if t2 != "-":
                    team2_rounds = int(t2)
            except (ValueError, AttributeError):
                pass

        # --- CT/T side rounds from half-score span ---
        half_score = mh.find("div", class_="results-center-half-score")
        if half_score:
            half_text = half_score.get_text(strip=True)
            half_text = half_text.strip("()")
            parts = half_text.split(";")
            if len(parts) == 2:
                try:
                    # First half: team1(T) : team2(CT)
                    t1_first, t2_first = parts[0].split(":")
                    # Second half: team1(CT) : team2(T)
                    t1_second, t2_second = parts[1].split(":")
                    team1_t_rounds = int(t1_first.strip())
                    team2_ct_rounds = int(t2_first.strip())
                    team1_ct_rounds = int(t1_second.strip())
                    team2_t_rounds = int(t2_second.strip())
                except (ValueError, IndexError):
                    pass

        winner = None
        if team1_rounds is not None and team2_rounds is not None:
            if team1_rounds > team2_rounds:
                winner = 1
            elif team2_rounds > team1_rounds:
                winner = 2

        result["maps"].append({
            "map_name": map_name,
            "team1_rounds": team1_rounds,
            "team2_rounds": team2_rounds,
            "team1_ct_rounds": team1_ct_rounds,
            "team1_t_rounds": team1_t_rounds,
            "team2_ct_rounds": team2_ct_rounds,
            "team2_t_rounds": team2_t_rounds,
            "winner_team_id": winner,
        })

    # --- Player stats via table.totalstats (overall only = first 2 tables) ---
    overall_tables = soup.find_all("table", class_="totalstats")[:2]
    for tidx, table in enumerate(overall_tables):
        team_id = tidx + 1
        for row in table.find_all("tr")[1:]:
            stat = _parse_player_stat_row_new(row, team_id)
            if stat:
                result["players"].append(stat)
    return result


def _parse_player_stat_row_new(row: Tag, team_id: int) -> Optional[dict[str, Any]]:
    """Parse player stats from HLTV table.totalstats by column order.

    Cell order: player_name, K-D, eK-eD, Swing%, ADR, ADR-adj, KAST%, KAST-adj, Rating
    """
    try:
        cells = row.find_all("td")
        if len(cells) < 9:
            return None

        # Player info from first cell
        player_cell = cells[0]
        player_link = player_cell.find("a", href=lambda h: h and "/player/" in str(h))
        player_id = None
        nickname = None
        if player_link:
            href = player_link.get("href", "")
            m = re.search(r"/player/(\d+)/", href)
            if m:
                player_id = int(m.group(1))
            link_text = player_link.get_text(strip=True)
            nm = re.search(r"'([^']+)'", link_text)
            nickname = nm.group(1) if nm else link_text

        texts = [c.get_text(strip=True) for c in cells]

        # K-D col (idx 1)
        kills = deaths = None
        kd_str = texts[1] if len(texts) > 1 else ""
        if "-" in kd_str and not kd_str.startswith("+"):
            parts = kd_str.split("-", 1)
            try:
                kills = int(parts[0])
                deaths = int(parts[1])
            except ValueError:
                pass

        # ADR col (idx 4)
        adr = None
        if len(texts) > 4:
            try:
                adr = round(float(texts[4]), 1)
            except ValueError:
                pass

        # Swing% col (idx 3) — percentage of rounds with opening kill or trade
        swing = None
        if len(texts) > 3:
            try:
                raw = texts[3].replace("%", "")
                swing = round(float(raw), 1)
            except ValueError:
                pass
        # KAST% col (idx 6)
        kast = None
        if len(texts) > 6:
            try:
                kast = round(float(texts[6].replace("%", "")), 1)
            except ValueError:
                pass

        # Rating col (idx 8)
        rating = None
        if len(texts) > 8:
            try:
                rating = round(float(texts[8]), 2)
            except ValueError:
                pass

        return {
            "player_id": player_id,
            "nickname": nickname,
            "team_id": team_id,
            "rating": rating,
            "adr": adr,
            "swing": swing,
            "kast": kast,
            "kd_diff": None,
            "kills": kills,
            "deaths": deaths,
        }
    except (AttributeError, ValueError, IndexError):
        return None

def parse_team_ranking_page(html: str) -> list[dict[str, Any]]:
    """Parse the /ranking/teams page.

    Each team is inside div.ranked-team:
      - .position span: "#1", "#2"
      - .name span: team name
      - .points span: "(991 HLTVpoints)"
    """
    soup = BeautifulSoup(html, "html.parser")
    teams: list[dict[str, Any]] = []

    ranked_teams = soup.find_all("div", class_="ranked-team")
    for rt in ranked_teams:
        parsed = _parse_ranked_team(rt)
        if parsed and parsed.get("team_id"):
            teams.append(parsed)

    return teams


def _parse_ranked_team(rt: Tag) -> Optional[dict[str, Any]]:
    try:
        rank_el = rt.find("span", class_="position")
        world_rank = None
        if rank_el:
            rank_text = rank_el.get_text(strip=True).lstrip("#")
            try:
                world_rank = int(rank_text)
            except ValueError:
                pass

        name_el = rt.find("span", class_="name")
        team_name = name_el.get_text(strip=True) if name_el else None

        team_link = rt.find("a", href=re.compile(r"/team/\d+/"))
        team_id = None
        if team_link:
            href = team_link.get("href", "")
            m = re.search(r"/team/(\d+)/", href)
            team_id = int(m.group(1)) if m else None

        if not team_id or not team_name:
            return None

        return {
            "team_id": team_id,
            "team_name": team_name,
            "world_rank": world_rank,
        }
    except (AttributeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Team detail page (players)
# ---------------------------------------------------------------------------

def parse_ranking_players(html: str) -> list[dict[str, Any]]:
    """Parse player rosters from the /ranking/teams page.

    Each div.ranked-team contains:
      - a[href^='/team/'] for team_id
      - table.lineup td.player-holder for individual players:
          a[href^='/player/'] with player_id in href
          img[alt] with full name format "Dan 'apEX' Madesclaire"
          div.nick with in-game nickname

    Returns list of dicts: player_id, player_name, nickname, team_id.

    Note: player_name uses the in-game nickname (e.g., "donk").
    The real name (if available) is stored in the `nickname` field.
    """
    soup = BeautifulSoup(html, "html.parser")
    players: list[dict[str, Any]] = []

    for rt in soup.find_all("div", class_="ranked-team"):
        team_link = rt.find("a", href=re.compile(r"/team/\d+/"))
        if not team_link:
            continue
        tm = re.search(r"/team/(\d+)/", team_link.get("href", ""))
        team_id = int(tm.group(1)) if tm else None
        if not team_id:
            continue

        lineup = rt.find("table", class_="lineup")
        if not lineup:
            continue

        for td in lineup.find_all("td", class_="player-holder"):
            a = td.find("a", href=re.compile(r"/player/\d+/"))
            if not a:
                continue
            href = a.get("href", "")
            m = re.search(r"/player/(\d+)/", href)
            pid = int(m.group(1)) if m else None
            if not pid:
                continue

            nick_div = td.find("div", class_="nick")
            nickname = nick_div.get_text(strip=True) if nick_div else None

            img = td.find("img")
            alt_text = img.get("alt", "") if img else ""
            # Extract real name from img alt text (format: "Dan [nickname] Madesclaire")
            real_name = alt_text if alt_text else None
            # player_name = nickname (game ID), nickname field stores the real name
            player_name = nickname or real_name or f"Player_{pid}"

            players.append({
                "player_id": pid,
                "player_name": player_name,
                "nickname": real_name,
                "team_id": team_id,
            })

    return players



# ---------------------------------------------------------------------------
# Event match list
# ---------------------------------------------------------------------------

def parse_event_match_list(html: str, event_id: int) -> list[dict[str, Any]]:
    """Parse event detail page for match links.

    Extracts all match IDs/URLs from an HLTV event page, along with
    team names where they can be inferred from the page structure.

    Returns list of dicts: match_id, match_url, event_id, team1_name, team2_name.
    """
    soup = BeautifulSoup(html, "html.parser")
    matches: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for a_tag in soup.find_all("a", href=re.compile(r"/matches/(\d+)/")):
        href = a_tag.get("href", "")
        m = re.search(r"/matches/(\d+)/", href)
        match_id = int(m.group(1)) if m else None
        if not match_id or match_id in seen_ids:
            continue
        seen_ids.add(match_id)

        # Try to extract team names from the match link's context
        team1_name: Optional[str] = None
        team2_name: Optional[str] = None

        # Strategy 1: inner div.team elements (event page match rows)
        team_divs = a_tag.find_all("div", class_=lambda c: c and "team" in c.lower() if c else False)
        if len(team_divs) >= 2:
            team1_name = team_divs[0].get_text(strip=True) or None
            team2_name = team_divs[1].get_text(strip=True) or None

        # Strategy 2: img alt attributes (team logos)
        if not team1_name and not team2_name:
            imgs = a_tag.find_all("img")
            alts = [img.get("alt", "") for img in imgs if img.get("alt")]
            if len(alts) >= 2:
                team1_name = alts[0]
                team2_name = alts[1]

        matches.append({
            "match_id": match_id,
            "match_url": href,
            "event_id": event_id,
            "team1_name": team1_name,
            "team2_name": team2_name,
        })

    return matches
