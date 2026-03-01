import os, json, logging
from pathlib import Path
logger = logging.getLogger(__name__)

AUTH_DIR = Path("/tmp/yahoo_auth")
TOKEN_FILE = AUTH_DIR / "token.json"
CREDS_FILE = AUTH_DIR / "private.json"

def setup_yahoo_auth():
    """Write Yahoo credentials and token from env vars to temp files so yfpy can read and refresh them."""
    AUTH_DIR.mkdir(parents=True, exist_ok=True)

    consumer_key = os.environ.get("YAHOO_CLIENT_ID")
    consumer_secret = os.environ.get("YAHOO_CLIENT_SECRET")
    if not consumer_key or not consumer_secret:
        logger.error("YAHOO_CLIENT_ID or YAHOO_CLIENT_SECRET missing!")
        raise ValueError("Missing Yahoo API credentials")

    creds = {"consumer_key": consumer_key, "consumer_secret": consumer_secret}
    CREDS_FILE.write_text(json.dumps(creds))
    logger.info("Credentials file written")

    token_json = os.environ.get("YAHOO_TOKEN_JSON")
    if token_json:
        try:
            parsed = json.loads(token_json)
            logger.info(f"Token parsed OK, keys: {list(parsed.keys())}")
            TOKEN_FILE.write_text(token_json)
            logger.info("Token file written to /tmp/yahoo_auth/token.json")
        except json.JSONDecodeError as e:
            logger.error(f"YAHOO_TOKEN_JSON is malformed JSON: {e}")
            raise
    else:
        logger.error("YAHOO_TOKEN_JSON is empty or missing!")
        raise ValueError("No Yahoo token found in environment")


class YahooFantasyClient:
    def __init__(self):
        self.league_id = os.environ.get("YAHOO_LEAGUE_ID")
        self.game_code = "nfl"
        self.game_id = int(os.environ.get("YAHOO_GAME_ID", "461"))
        self._query = None

    def _get_query(self):
        if self._query is None:
            logger.info("=== STARTING YAHOO AUTH ===")
            logger.info(f"League ID: {self.league_id}, Game ID: {self.game_id}")

            try:
                setup_yahoo_auth()
            except Exception as e:
                logger.error(f"Yahoo auth setup failed: {e}")
                raise

            logger.info("Creating YahooFantasySportsQuery object...")
            try:
                from yfpy.query import YahooFantasySportsQuery
                self._query = YahooFantasySportsQuery(
                    AUTH_DIR,
                    self.league_id,
                    self.game_id,
                    self.game_code,
                    consumer_key=os.environ.get("YAHOO_CLIENT_ID"),
                    consumer_secret=os.environ.get("YAHOO_CLIENT_SECRET")
                )
                logger.info("=== YAHOO AUTH COMPLETE ===")
            except Exception as e:
                logger.error(f"Failed to create YahooFantasySportsQuery: {e}")
                raise

        return self._query

    def _parse_team(self, t):
        try:
            d = t.get("team", t) if isinstance(t, dict) else t
            if isinstance(d, dict):
                s = d.get("team_standings", {})
                totals = s.get("outcome_totals", {})
                manager = d.get("managers", {}).get("manager", {}).get("nickname", "Unknown")
                return {
                    "rank": s.get("rank", "?"),
                    "name": d.get("name", "Unknown").decode() if isinstance(d.get("name", "Unknown"), bytes) else d.get("name", "Unknown"),
                    "manager": manager,
                    "wins": totals.get("wins", 0),
                    "losses": totals.get("losses", 0),
                    "points_for": s.get("points_for", 0),
                }
            else:
                s = getattr(d, "team_standings", None)
                return {
                    "rank": getattr(s, "rank", "?"),
                    "name": str(getattr(d, "name", "Unknown")),
                    "wins": getattr(getattr(s, "outcome_totals", None), "wins", 0),
                    "losses": getattr(getattr(s, "outcome_totals", None), "losses", 0),
                    "points_for": getattr(s, "points_for", 0),
                }
        except Exception as e:
            return {"error": str(e)}

    def get_league_info(self):
        try:
            return {"name": str(self._get_query().get_league_info().name), "season": "2025"}
        except Exception as e:
            logger.error(f"get_league_info failed: {e}")
            return {"error": str(e)}

    def get_standings(self):
        try:
            logger.info("Getting standings...")
            standings = self._get_query().get_league_standings()
            logger.info(f"Got standings: {type(standings)}")
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
