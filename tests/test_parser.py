"""Tests for the parser module — HTML parsing logic."""

from parser import (
    parse_events_page,
    parse_results_page,
    parse_team_ranking_page,
    parse_ranking_players,
)
from parser.parsers import parse_match_detail


# ---------------------------------------------------------------------------
# Sample HTML fragments (simulating HLTV structure)
# ---------------------------------------------------------------------------

SAMPLE_EVENTS_HTML = '''
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
'''

SAMPLE_RESULTS_HTML = '''
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
'''

SAMPLE_RANKING_HTML = '''
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
'''

SAMPLE_RANKING_PLAYERS_HTML = '''
<div class="ranked-team">
  <a href="/team/123/faze/"></a>
  <table class="lineup">
    <tr>
      <td class="player-holder">
        <a href="/player/9876/"></a>
        <div class="nick">ropz</div>
        <img alt="Robin "ropz" Kool">
      </td>
    </tr>
  </table>
</div>
'''


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
        html = SAMPLE_EVENTS_HTML + SAMPLE_EVENTS_HTML  # duplicate
        events = parse_events_page(html)
        assert len(events) == 2  # deduplicated by event_id


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
        """Should handle match detail page with no maps/players gracefully."""
        result = parse_match_detail("<html><body>No data</body></html>")
        assert result is not None
        assert result["maps"] == []
        assert result["players"] == []

    def test_parse_with_date(self):
        """Should extract date from data-unix attribute."""
        html = '''<div class="date" data-unix="1700000000000"></div>'''
        result = parse_match_detail(html)
        assert result is not None
        assert "2023-11-14" in result.get("match_datetime", "")
