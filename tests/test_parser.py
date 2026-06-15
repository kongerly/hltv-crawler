"""Tests for the parser module — HTML parsing logic."""

from parser import (
    parse_event_match_list,
    parse_events_page,
    parse_ranking_players,
    parse_results_page,
    parse_team_ranking_page,
)
from parser.parsers import parse_match_detail

# ---------------------------------------------------------------------------
# Sample HTML fragments (simulating HLTV structure)
# ---------------------------------------------------------------------------

SAMPLE_EVENTS_HTML = """
<div class="ongoing-event-holder">
  <a href="/events/1234/some-event/">
    Some Event $100,000
  </a>
</div>
<div class="events-holder">
  <a href="/events/5678/another-event/">
    Another Event
  </a>
</div>
"""

SAMPLE_RESULTS_HTML = """
<div class="result-con">
  <a href="/matches/1001/faze-vs-navi/">
    <table>
      <tr>
        <td class="team-cell"><div class="team">FaZe</div></td>
        <td class="result-score">2-1</td>
        <td class="team-cell"><div class="team team-won">NaVi</div></td>
        <td class="event"><span class="event-name">IEM Katowice</span></td>
        <td class="star-cell"><div class="map-text">bo3</div></td>
      </tr>
    </table>
  </a>
</div>
"""

SAMPLE_RANKING_HTML = """
<div class="ranked-team">
  <span class="position">#1</span>
  <span class="name">FaZe</span>
  <a href="/team/123/faze/">FaZe</a>
</div>
<div class="ranked-team">
  <span class="position">#2</span>
  <span class="name">NaVi</span>
  <a href="/team/456/navi/">NaVi</a>
</div>
"""

SAMPLE_RANKING_PLAYERS_HTML = """
<div class="ranked-team">
  <a href="/team/123/faze/"></a>
  <table class="lineup">
    <tr>
      <td class="player-holder">
        <a href="/player/9876/"></a>
        <div class="nick">ropz</div>
        <img alt="Robin \"ropz\" Kool">
      </td>
    </tr>
  </table>
</div>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseEvents:
    def test_parse_events_page(self):
        events = parse_events_page(SAMPLE_EVENTS_HTML)
        assert len(events) == 2
        assert any(e["event_name"] == "Some Event" for e in events)
        assert any(e["event_id"] == 5678 for e in events)

    def test_parse_events_empty(self):
        events = parse_events_page("<html></html>")
        assert events == []

    def test_parse_events_dedup(self):
        html = SAMPLE_EVENTS_HTML + SAMPLE_EVENTS_HTML
        events = parse_events_page(html)
        assert len(events) == 2


class TestParseResults:
    def test_parse_results_page(self):
        matches = parse_results_page(SAMPLE_RESULTS_HTML)
        assert len(matches) == 1
        assert matches[0]["match_id"] == 1001
        assert matches[0]["team1_name"] == "FaZe"
        assert matches[0]["team2_name"] == "NaVi"

    def test_parse_results_empty(self):
        matches = parse_results_page("<html></html>")
        assert matches == []


class TestParseTeamRankings:
    def test_parse_team_ranking_page(self):
        teams = parse_team_ranking_page(SAMPLE_RANKING_HTML)
        assert len(teams) == 2
        assert teams[0]["team_name"] == "FaZe"
        assert teams[0]["world_rank"] == 1
        assert teams[0]["team_id"] == 123

    def test_parse_ranking_empty(self):
        teams = parse_team_ranking_page("<html></html>")
        assert teams == []


class TestParseRankingPlayers:
    def test_parse_ranking_players(self):
        players = parse_ranking_players(SAMPLE_RANKING_PLAYERS_HTML)
        assert len(players) == 1
        assert players[0]["player_name"] == "ropz"
        assert players[0]["team_id"] == 123
        assert players[0]["player_id"] == 9876

    def test_parse_ranking_players_empty(self):
        players = parse_ranking_players("<html></html>")
        assert players == []


class TestParseMatchDetail:
    def test_parse_minimal_html(self):
        result = parse_match_detail("<html><body>No data</body></html>")
        assert result is not None
        assert result["maps"] == []
        assert result["players"] == []

    def test_parse_with_date(self):
        html = """<div class="date" data-unix="1700000000000"></div>"""
        result = parse_match_detail(html)
        assert result is not None
        assert "2023-11-14" in result.get("match_datetime", "")

    def test_parse_player_stats_with_swing(self):
        html = """
        <table class="totalstats">
          <tr><th>Player</th><th>K-D</th><th>+/-</th><th>Swing%</th><th>ADR</th><th>ADR-adj</th><th>KAST%</th><th>KAST-adj</th><th>Rating</th></tr>
          <tr>
            <td><a href="/player/9876/"><img alt="Robin \'ropz\' Kool"></a></td>
            <td>22-15</td>
            <td>+7</td>
            <td>72.3%</td>
            <td>95.3</td>
            <td>90.1</td>
            <td>78.5%</td>
            <td>75.2</td>
            <td>1.25</td>
          </tr>
        </table>
        <table class="totalstats">
          <tr><th>Player</th><th>K-D</th><th>+/-</th><th>Swing%</th><th>ADR</th><th>ADR-adj</th><th>KAST%</th><th>KAST-adj</th><th>Rating</th></tr>
          <tr>
            <td><a href="/player/5432/"><img alt="Ilya \'m0NESY\' Osipov"></a></td>
            <td>18-14</td>
            <td>+4</td>
            <td>68.0%</td>
            <td>82.1</td>
            <td>78.4</td>
            <td>85.1%</td>
            <td>80.6</td>
            <td>1.42</td>
          </tr>
        </table>
        """
        result = parse_match_detail(html)
        assert result is not None
        assert len(result["players"]) == 2

        p1 = result["players"][0]
        assert p1["player_id"] == 9876
        assert p1["team_id"] == 1
        assert p1["kills"] == 22
        assert p1["deaths"] == 15
        assert p1["swing"] == 72.3
        assert p1["adr"] == 95.3
        assert p1["kast"] == 78.5
        assert p1["rating"] == 1.25

        p2 = result["players"][1]
        assert p2["player_id"] == 5432
        assert p2["team_id"] == 2
        assert p2["kills"] == 18
        assert p2["deaths"] == 14
        assert p2["swing"] == 68.0
        assert p2["adr"] == 82.1
        assert p2["kast"] == 85.1
        assert p2["rating"] == 1.42


# ---------------------------------------------------------------------------
# Event match list
# ---------------------------------------------------------------------------

SAMPLE_EVENT_PAGE_HTML = """
<div class="event-page">
  <div class="event-info">
    <h1>IEM Cologne 2024</h1>
  </div>
  <div class="results">
    <div class="result-con">
      <a href="/matches/1001/team-a-vs-team-b/">
        <div class="team team1">Team A</div>
        <div class="score">2-0</div>
        <div class="team team2">Team B</div>
      </a>
    </div>
    <div class="result-con">
      <a href="/matches/1002/team-c-vs-team-d/">
        <div class="team team1">Team C</div>
        <div class="score">1-2</div>
        <div class="team team2">Team D</div>
      </a>
    </div>
  </div>
</div>
"""


class TestParseEventMatchList:
    def test_parse_event_match_list(self):
        matches = parse_event_match_list(SAMPLE_EVENT_PAGE_HTML, event_id=9999)
        assert len(matches) == 2
        assert matches[0]["match_id"] == 1001
        assert matches[0]["event_id"] == 9999
        assert matches[0]["team1_name"] == "Team A"
        assert matches[0]["team2_name"] == "Team B"
        assert matches[1]["match_id"] == 1002
        assert matches[1]["event_id"] == 9999
        assert matches[1]["team1_name"] == "Team C"
        assert matches[1]["team2_name"] == "Team D"

    def test_parse_event_match_list_empty(self):
        matches = parse_event_match_list("<html></html>", event_id=0)
        assert matches == []

    def test_parse_event_match_list_dedup(self):
        matches = parse_event_match_list(SAMPLE_EVENT_PAGE_HTML * 2, event_id=9999)
        assert len(matches) == 2
