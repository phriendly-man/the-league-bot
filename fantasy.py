import os, json, logging
from pathlib import Path
logger = logging.getLogger(__name__)

class YahooFantasyClient:
    def __init__(self):
        self.league_id = os.environ.get("YAHOO_LEAGUE_ID")
        self.game_code = "nfl"
        self.game_id = int(os.environ.get("YAHOO_GAME_ID", "461"))
        self._query = None

    def _get_query(self):
        if self._query is None:
            from yfpy.query import YahooFantasySportsQuery
            auth_dir = Path("/tmp/yahoo_auth")
            auth_dir.mkdir(exist_ok=True)
            creds = {"consumer_key": os.environ.get("YAHOO_CLIENT_ID"), "consumer_secret": os.environ.get("YAHOO_CLIENT_SECRET")}
            (auth_dir / "private.json").write_text(json.dumps(creds))
            token_json = os.environ.get("YAHOO_TOKEN_JSON")
            if token_json:
                (auth_dir / "token.json").write_text(token_json)
            self._query = YahooFantasySportsQuery(auth_dir, self.league_id, game_id=self.game_id, game_code=self.game_code, consumer_key=os.environ.get("YAHOO_CLIENT_ID"), consumer_secret=os.environ.get("YAHOO_CLIENT_SECRET"))
        return self._query

    def get_league_info(self):
        try:
            return {"name": str(self._get_query().get_league_info().name), "season": "2025"}
        except Exception as e:
            return {"error": str(e)}

    def get_standings(self):
        try:
            standings = self._get_query().get_league_standings()
            result = []
            teams_list = standings.teams.team if hasattr(standings.teams, 'team') else standings.teams
            for team in (teams_list if isinstance(teams_list, list) else [teams_list]):
                result.append({"rank": team.team_standings.rank, "name": str(team.name), "wins": team.team_standings.outcome_totals.wins, "losses": team.team_standings.outcome_totals.losses, "points_for": team.team_standings.points_for})
            return result
        except Exception as e:
            return [{"error": str(e)}]

    def get_scoreboard(self, week=None):
        try:
            q = self._get_query()
            w = week or q.get_league_info().current_week
            scoreboard = q.get_league_scoreboard_by_week(w)
            matchups = []
            for matchup in scoreboard.matchups.matchup:
                teams = matchup.teams.team
                if len(teams) >= 2:
                    matchups.append({"week": matchup.week, "team1": {"name": str(teams[0].name), "points": teams[0].team_points.total}, "team2": {"name": str(teams[1].name), "points": teams[1].team_points.total}})
            return matchups
        except Exception as e:
            return [{"error": str(e)}]

    def get_league_teams(self):
        try:
            return [{"team_id": t.team_id, "name": str(t.name)} for t in self._get_query().get_league_teams().teams.team]
        except Exception as e:
            return [{"error": str(e)}]

    def get_team_roster(self, team_name):
        try:
            q = self._get_query()
            all_teams = q.get_league_teams()
            target = next((t for t in all_teams.teams.team if team_name.lower() in str(t.name).lower()), None)
            if not target:
                return {"error": "Team not found"}
            roster = q.get_team_roster_by_week(target.team_id)
            return {"team_name": str(target.name), "players": [{"name": str(p.name.full), "position": str(p.display_position)} for p in roster.roster.players.player]}
        except Exception as e:
            return {"error": str(e)}

    def get_player_stats(self, player_name, week=None):
        try:
            players = self._get_query().get_league_players(player_filter=player_name, number_of_players=3)
            if not players:
                return {"error": "Player not found"}
            p = players[0]
            return {"name": str(p.name.full), "position": str(p.display_position)}
        except Exception as e:
            return {"error": str(e)}

    def get_league_transactions(self):
        try:
            transactions = self._get_query().get_league_transactions()
            return [{"type": str(tx.type)} for tx in (transactions.transactions.transaction if hasattr(transactions, "transactions") else [])[:5]]
        except Exception as e:
            return [{"error": str(e)}]
