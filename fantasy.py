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
                                    game_id=self.game_id,
                                    game_code=self.game_code,
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
                                                    retimport os, json, logging
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
                                        game_id=self.game_id,
                                        game_code=self.game_code,
                                        consumer_key=os.environ.get("YAHOO_CLIENT_ID"),
                                        consumer_secret=os.environ.get("YAHOO_CLIENT_SECRET")
                )
                logger.info("
