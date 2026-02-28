import os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
client_id = os.environ.get("YAHOO_CLIENT_ID")
client_secret = os.environ.get("YAHOO_CLIENT_SECRET")
league_id = os.environ.get("YAHOO_LEAGUE_ID")
game_id = int(os.environ.get("YAHOO_GAME_ID", "449"))
auth_dir = Path("./yahoo_auth_temp")
auth_dir.mkdir(exist_ok=True)
(auth_dir / "private.json").write_text(json.dumps({"consumer_key": client_id, "consumer_secret": client_secret}))
from yfpy.query import YahooFantasySportsQuery
try:
    q = YahooFantasySportsQuery(auth_dir, league_id, game_id=game_id, game_code="nfl", consumer_key=client_id, consumer_secret=client_secret)
except TypeError:
    q = YahooFantasySportsQuery(league_id=league_id, game_code="nfl", game_id=game_id, yahoo_consumer_key=client_id, yahoo_consumer_secret=client_secret, env_file_location=auth_dir)
print("Browser should open - log in to Yahoo and approve access...")
q.get_league_info()
for p in [auth_dir/"token.json", auth_dir/"yahoo_oauth.json", Path("token.json")]:
    if p.exists():
        print("TOKEN:", p.read_text())
        break
