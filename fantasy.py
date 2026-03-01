import os, json, logging
from pathlib import Path
logger = logging.getLogger(__name__)

AUTH_DIR = Path("/tmp/yahoo_auth")
TOKEN_FILE = AUTH_DIR / "token.json"
CREDS_FILE = AUTH_DIR / "private.json"

def setup_yahoo_auth():
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    consumer_key = os.environ.get("YAHOO_CLIENT_ID")
    consumer_secret = os.environ.get("YAHOO_CLIENT_SECRET")
    if not consumer_key or not consumer_secret:
        raise ValueError("Missing Yahoo API credentials")
    CREDS_FILE.write_text(json.dumps({"consumer_key": consumer_key, "consumer_secret": consumer_secret}))
    logger.info("Credentials file written")
    token_json = os.environ.get("YAHOO_TOKEN_JSON")
    if not token_json:
        raise ValueError("No Yahoo token found in environment")
    try:
        parsed = json.loads(token_json)
        logger.info(f"Token parsed OK, keys: {list(parsed.keys())}")
        TOKEN_FILE.write_text(token_json)
        logger.info("Token file written")
    except json.JSONDecodeError as e:
        logger.error(f"YAHOO_TOKEN_JSON malformed: {e}")
        raise


class YahooFantasyClient:
    def __init__(self):
        self.league_id = os.environ.get("YAHOO_LEAGUE_ID")
        self.game_id = int(os.environ.get("YAHOO_GAME_ID", "461"))
        self._query = None

    def _get_query(self):
        if self._query is None:
            logger.info("=== STARTING YAHOO AUTH ===")
            setup_yahoo_auth()
            from yfpy.query import YahooFantasySportsQuery
            self._query = YahooFantasySportsQuery(
                auth_dir=AUTH_DIR,
                league_id=self.league_id,
                game_id=self.game_id,
                game_code="nfl",
                consumer_key=os.environ.get("YAHOO_CLIENT_ID"),
                consumer_secret=os.environ.get("YAHOO_CLIENT_SECRET")
            )
            logger.info("=== YAHOO AUTH COMPLETE ===")
        return self._query

    def _parse_team(self, t):
        try:
            d = t.get("team", t) if isinstance(t, dict) else t
            if isinstance(d, dict):
                s = d.get("team_standings", {})
                totals = s.get("outcome_totals", {})
                name = d.get("name", "Unknown")
                return {
                    "rank": s.get("rank", "?"),
                    "name": name.decode() if isinstance(name, bytes) else name,
                    "manager": d.get("managers", {}).get("manager", {}).get("nickname", "Unknown"),
                    "wins": totals.get("wins", 0),
                    "losses": totals.get("losses", 0),
                    "points_for": s.get("points_for", 0),
                }
            else:
                s = getattr(d, "team_standings", None)
                ot = getattr(s, "outcome_totals", None)
                return {
                    "rank": getattr(s, "rank", "?"),
                    "name": str(getattr(d, "name", "Unknown")),
                    "wins": getattr(ot, "wins", 0),
                    "losses": getattr(ot, "losses", 0),
                    "points_for": getattr(s, "points_for", 0),
                }
        except Exception as e:
            return {"error": str(e)}

    def get_standings(self):
        try:
            logger.info("Getting standings...")
            standings = self._get_query().get_league_standings()
            teams = standings.teams.team if hasattr(standings.teams, "team") else standings.teams
            if not isinstance(teams, list):
                teams = [teams]
            return [self._parse_team(t) for t in teams]
        except Exception as e:
            logger.error(f"get_standings failed: {e}")
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
                    matchups.append({
                        "week": matchup.week,
                        "team1": {"name": str(teams[0].name), "points": teams[0].team_points.total},
                        "team2": {"name": str(teams[1].name), "points": teams[1].team_points.total}
                    })
            return matchups
        except Exception as e:
            logger.error(f"get_scoreboard failed: {e}")
            return [{"error": str(e)}]

    def get_league_teams(self):
        try:
            return [{"team_id": t.team_id, "name": str(t.name)} for t in self._get_query().get_league_teams().teams.team]
        except Exception as e:
            logger.error(f"get_league_teams failed: {e}")
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
            logger.error(f"get_team_roster failed: {e}")
            return {"error": str(e)}

    def get_player_stats(self, player_name, week=None):
        try:
            players = self._get_query().get_league_players(player_filter=player_name, number_of_players=3)
            if not players:
                return {"error": "Player not found"}
            p = players[0]
            return {"name": str(p.name.full), "position": str(p.display_position)}
        except Exception as e:
            logger.error(f"get_player_stats failed: {e}")
            return {"error": str(e)}

    def get_league_transactions(self):
        try:
            transactions = self._get_query().get_league_transactions()
            return [{"type": str(tx.type)} for tx in (transactions.transactions.transaction if hasattr(transactions, "transactions") else [])[:5]]
        except Exception as e:
            logger.error(f"get_league_transactions failed: {e}")
            return [{"error": str(e)}]
