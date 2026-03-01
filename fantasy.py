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


def _safe(val, default="Unknown"):
    if val is None:
        return default
    if isinstance(val, bytes):
        return val.decode()
    return val


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
                AUTH_DIR,
                self.league_id,
                game_id=self.game_id,
                game_code="nfl",
                consumer_key=os.environ.get("YAHOO_CLIENT_ID"),
                consumer_secret=os.environ.get("YAHOO_CLIENT_SECRET")
            )
            logger.info("=== YAHOO AUTH COMPLETE ===")
        return self._query

    # ── helpers ──────────────────────────────────────────────────────────────

    def _parse_team(self, t):
        try:
            d = t.get("team", t) if isinstance(t, dict) else t
            if isinstance(d, dict):
                s = d.get("team_standings", {})
                totals = s.get("outcome_totals", {})
                return {
                    "rank": s.get("rank", "?"),
                    "name": _safe(d.get("name", "Unknown")),
                    "manager": d.get("managers", {}).get("manager", {}).get("nickname", "Unknown"),
                    "wins": totals.get("wins", 0),
                    "losses": totals.get("losses", 0),
                    "ties": totals.get("ties", 0),
                    "points_for": s.get("points_for", 0),
                    "points_against": s.get("points_against", 0),
                }
            else:
                s = getattr(d, "team_standings", None)
                ot = getattr(s, "outcome_totals", None)
                return {
                    "rank": getattr(s, "rank", "?"),
                    "name": _safe(str(getattr(d, "name", "Unknown"))),
                    "wins": getattr(ot, "wins", 0),
                    "losses": getattr(ot, "losses", 0),
                    "ties": getattr(ot, "ties", 0),
                    "points_for": getattr(s, "points_for", 0),
                    "points_against": getattr(s, "points_against", 0),
                }
        except Exception as e:
            return {"error": str(e)}

    def _teams_list(self, raw):
        teams = getattr(raw, "teams", raw) if not isinstance(raw, dict) else raw.get("teams", raw)
        teams = getattr(teams, "team", teams) if not isinstance(teams, (list, dict)) else teams
        if isinstance(teams, dict):
            teams = teams.get("team", [teams])
        if not isinstance(teams, list):
            teams = [teams]
        return teams

    # ── league-level ─────────────────────────────────────────────────────────

    def get_league_info(self):
        try:
            info = self._get_query().get_league_info()
            return {
                "name": _safe(str(getattr(info, "name", "Unknown"))),
                "season": getattr(info, "season", "Unknown"),
                "num_teams": getattr(info, "num_teams", "Unknown"),
                "current_week": getattr(info, "current_week", "Unknown"),
                "start_week": getattr(info, "start_week", 1),
                "end_week": getattr(info, "end_week", 17),
            }
        except Exception as e:
            logger.error(f"get_league_info failed: {e}")
            return {"error": str(e)}

    def get_league_settings(self):
        try:
            s = self._get_query().get_league_settings()
            return json.loads(json.dumps(s, default=str))
        except Exception as e:
            logger.error(f"get_league_settings failed: {e}")
            return {"error": str(e)}

    def get_standings(self):
        try:
            logger.info("Getting standings...")
            standings = self._get_query().get_league_standings()
            return [self._parse_team(t) for t in self._teams_list(standings)]
        except Exception as e:
            logger.error(f"get_standings failed: {e}")
            return [{"error": str(e)}]

    def get_scoreboard(self, week=None):
        try:
            q = self._get_query()
            w = week or getattr(q.get_league_info(), "current_week", None)
            scoreboard = q.get_league_scoreboard_by_week(w)
            matchups_raw = getattr(scoreboard, "matchups", scoreboard)
            matchups_raw = getattr(matchups_raw, "matchup", matchups_raw)
            if not isinstance(matchups_raw, list):
                matchups_raw = [matchups_raw]
            matchups = []
            for m in matchups_raw:
                try:
                    teams = getattr(getattr(m, "teams", None), "team", [])
                    if not isinstance(teams, list):
                        teams = [teams]
                    if len(teams) >= 2:
                        matchups.append({
                            "week": getattr(m, "week", w),
                            "team1": {"name": _safe(str(getattr(teams[0], "name", "?"))), "points": str(getattr(getattr(teams[0], "team_points", None), "total", "?"))},
                            "team2": {"name": _safe(str(getattr(teams[1], "name", "?"))), "points": str(getattr(getattr(teams[1], "team_points", None), "total", "?"))},
                        })
                except Exception as me:
                    matchups.append({"error": str(me)})
            return {"week": w, "matchups": matchups}
        except Exception as e:
            logger.error(f"get_scoreboard failed: {e}")
            return {"error": str(e)}

    def get_matchups_by_week(self, week):
        try:
            raw = self._get_query().get_league_matchups_by_week(week)
            return json.loads(json.dumps(raw, default=str))
        except Exception as e:
            logger.error(f"get_matchups_by_week failed: {e}")
            return {"error": str(e)}

    def get_league_teams(self):
        try:
            raw = self._get_query().get_league_teams()
            teams = self._teams_list(raw)
            return [{"team_id": getattr(t, "team_id", "?"), "name": _safe(str(getattr(t, "name", "?"))), "manager": _safe(str(getattr(getattr(getattr(t, "managers", None), "manager", None), "nickname", "?")))} for t in teams]
        except Exception as e:
            logger.error(f"get_league_teams failed: {e}")
            return [{"error": str(e)}]

    def get_league_draft_results(self):
        try:
            raw = self._get_query().get_league_draft_results()
            picks = getattr(raw, "draft_results", raw)
            picks = getattr(picks, "draft_result", picks)
            if not isinstance(picks, list):
                picks = [picks]
            return [{"pick": getattr(p, "pick", "?"), "round": getattr(p, "round", "?"), "team_key": getattr(p, "team_key", "?"), "player_key": getattr(p, "player_key", "?")} for p in picks]
        except Exception as e:
            logger.error(f"get_league_draft_results failed: {e}")
            return [{"error": str(e)}]

    def get_league_transactions(self, count=20):
        try:
            raw = self._get_query().get_league_transactions()
            txns = getattr(raw, "transactions", raw)
            txns = getattr(txns, "transaction", txns)
            if not isinstance(txns, list):
                txns = [txns]
            result = []
            for tx in txns[:count]:
                result.append({
                    "type": _safe(str(getattr(tx, "type", "?"))),
                    "status": _safe(str(getattr(tx, "status", "?"))),
                    "timestamp": str(getattr(tx, "timestamp", "?")),
                })
            return result
        except Exception as e:
            logger.error(f"get_league_transactions failed: {e}")
            return [{"error": str(e)}]

    def get_league_players(self, search=None, count=25):
        try:
            raw = self._get_query().get_league_players(player_filter=search, number_of_players=count)
            if not raw:
                return []
            players = raw if isinstance(raw, list) else [raw]
            return [{"name": _safe(str(getattr(getattr(p, "name", None), "full", getattr(p, "name", "?")))), "position": _safe(str(getattr(p, "display_position", "?"))), "team": _safe(str(getattr(p, "editorial_team_abbr", "?"))), "status": _safe(str(getattr(p, "status", "Active")))} for p in players]
        except Exception as e:
            logger.error(f"get_league_players failed: {e}")
            return [{"error": str(e)}]

    # ── team-level ────────────────────────────────────────────────────────────

    def get_team_roster(self, team_name, week=None):
        try:
            q = self._get_query()
            teams = self._teams_list(q.get_league_teams())
            target = next((t for t in teams if team_name.lower() in _safe(str(getattr(t, "name", ""))).lower()), None)
            if not target:
                return {"error": f"Team '{team_name}' not found"}
            tid = getattr(target, "team_id", None)
            roster = q.get_team_roster_by_week(tid, week) if week else q.get_team_roster_by_week(tid)
            players = getattr(getattr(getattr(roster, "roster", roster), "players", None), "player", [])
            if not isinstance(players, list):
                players = [players]
            return {
                "team_name": _safe(str(getattr(target, "name", team_name))),
                "week": week,
                "players": [{"name": _safe(str(getattr(getattr(p, "name", None), "full", getattr(p, "name", "?")))), "position": _safe(str(getattr(p, "display_position", "?"))), "selected_position": _safe(str(getattr(getattr(p, "selected_position", None), "position", "?"))), "status": _safe(str(getattr(p, "status", "Active"))), "team": _safe(str(getattr(p, "editorial_team_abbr", "?")))} for p in players]
            }
        except Exception as e:
            logger.error(f"get_team_roster failed: {e}")
            return {"error": str(e)}

    def get_team_stats(self, team_name, week=None):
        try:
            q = self._get_query()
            teams = self._teams_list(q.get_league_teams())
            target = next((t for t in teams if team_name.lower() in _safe(str(getattr(t, "name", ""))).lower()), None)
            if not target:
                return {"error": f"Team '{team_name}' not found"}
            tid = getattr(target, "team_id", None)
            raw = q.get_team_stats_by_week(tid, week) if week else q.get_team_stats(tid)
            return json.loads(json.dumps(raw, default=str))
        except Exception as e:
            logger.error(f"get_team_stats failed: {e}")
            return {"error": str(e)}

    def get_team_matchups(self, team_name):
        try:
            q = self._get_query()
            teams = self._teams_list(q.get_league_teams())
            target = next((t for t in teams if team_name.lower() in _safe(str(getattr(t, "name", ""))).lower()), None)
            if not target:
                return {"error": f"Team '{team_name}' not found"}
            tid = getattr(target, "team_id", None)
            raw = q.get_team_matchups(tid)
            return json.loads(json.dumps(raw, default=str))
        except Exception as e:
            logger.error(f"get_team_matchups failed: {e}")
            return {"error": str(e)}

    def get_team_draft_results(self, team_name):
        try:
            q = self._get_query()
            teams = self._teams_list(q.get_league_teams())
            target = next((t for t in teams if team_name.lower() in _safe(str(getattr(t, "name", ""))).lower()), None)
            if not target:
                return {"error": f"Team '{team_name}' not found"}
            tid = getattr(target, "team_id", None)
            raw = q.get_team_draft_results(tid)
            return json.loads(json.dumps(raw, default=str))
        except Exception as e:
            logger.error(f"get_team_draft_results failed: {e}")
            return {"error": str(e)}

    # ── player-level ──────────────────────────────────────────────────────────

    def get_player_stats(self, player_name, week=None):
        try:
            q = self._get_query()
            players = q.get_league_players(player_filter=player_name, number_of_players=5)
            if not players:
                return {"error": f"Player '{player_name}' not found"}
            p = players[0] if isinstance(players, list) else players
            result = {
                "name": _safe(str(getattr(getattr(p, "name", None), "full", player_name))),
                "position": _safe(str(getattr(p, "display_position", "?"))),
                "team": _safe(str(getattr(p, "editorial_team_abbr", "?"))),
                "status": _safe(str(getattr(p, "status", "Active"))),
            }
            player_key = getattr(p, "player_key", None)
            if player_key:
                try:
                    if week:
                        stats = q.get_player_stats_by_week(player_key, week)
                    else:
                        stats = q.get_player_stats_for_season(player_key)
                    result["stats"] = json.loads(json.dumps(stats, default=str))
                except Exception as se:
                    result["stats_error"] = str(se)
            return result
        except Exception as e:
            logger.error(f"get_player_stats failed: {e}")
            return {"error": str(e)}

    def get_player_ownership(self, player_name):
        try:
            q = self._get_query()
            players = q.get_league_players(player_filter=player_name, number_of_players=3)
            if not players:
                return {"error": "Player not found"}
            p = players[0] if isinstance(players, list) else players
            player_key = getattr(p, "player_key", None)
            if not player_key:
                return {"error": "Could not get player key"}
            raw = q.get_player_ownership(player_key)
            return json.loads(json.dumps(raw, default=str))
        except Exception as e:
            logger.error(f"get_player_ownership failed: {e}")
            return {"error": str(e)}
