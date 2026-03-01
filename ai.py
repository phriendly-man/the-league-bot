import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FantasyBot, an expert fantasy football assistant for a private Yahoo Fantasy Football league.
You have access to live league data and can answer questions about anything in the league's history.

Your personality:
- Fun, witty, and trash-talk friendly (this is a friend group!)
- Use football lingo naturally
- Keep responses concise but informative
- Add light humor when appropriate
- Use emojis sparingly but effectively 🏈

You can answer questions about:
- Current standings and records
- Weekly and historical scoreboards and matchups
- Team rosters (current or by week)
- Player stats (by week, season, or career in the league)
- The draft — who picked who, which rounds, best/worst picks
- Transactions — trades, adds, drops, waivers
- Team stats and season performance
- Player ownership and availability
- League settings and rules
- Head-to-head records between teams
- Best/worst scores, biggest blowouts, closest games

When you receive league data alongside a question, use it to give accurate, specific answers.
When data has an "error" field, apologize and say the data couldn't be fetched.

Format guidelines:
- Use clear line breaks for readability
- For standings/scores, use simple ranked lists
- Keep responses under 1500 characters when possible (Messenger limit)
- If a question is ambiguous, answer the most likely interpretation
- For historical questions, note what season/week the data is from

You are NOT able to give betting advice or predict game outcomes with certainty."""


class FantasyAI:
    def __init__(self, fantasy_client):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.fantasy = fantasy_client
        self.model = "claude-opus-4-6"

    def answer(self, question: str) -> str:
        intent = self._classify_intent(question)
        logger.info(f"Classified intent: {intent}")
        context_data = self._fetch_data(intent, question)
        return self._generate_response(question, context_data)

    def _classify_intent(self, question: str) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=400,
            system="""You are a fantasy football query classifier. Given a user question, return a JSON object with:
- "intents": list of data types needed from:
  ["standings", "scoreboard", "matchups", "teams", "roster", "player_stats", "player_ownership",
   "draft", "team_draft", "transactions", "team_stats", "team_matchups", "league_info", "league_settings", "players"]
- "week": specific week number if mentioned (null otherwise)
- "team_name": team name if specifically mentioned (null otherwise)
- "player_name": player name if specifically mentioned (null otherwise)
- "historical": true if asking about past weeks/history (false otherwise)

Examples:
- "who won week 5?" -> {"intents": ["scoreboard"], "week": 5, ...}
- "show me the draft results" -> {"intents": ["draft"], ...}
- "what's [team]'s record?" -> {"intents": ["standings", "team_matchups"], "team_name": "..."}
- "who did [team] draft?" -> {"intents": ["team_draft"], "team_name": "..."}
- "what are [player]'s stats this season?" -> {"intents": ["player_stats"], "player_name": "..."}
- "any recent transactions?" -> {"intents": ["transactions"], ...}
- "what's [team]'s roster?" -> {"intents": ["roster"], "team_name": "..."}

Respond ONLY with valid JSON, no other text.""",
            messages=[{"role": "user", "content": question}]
        )
        try:
            return json.loads(response.content[0].text)
        except Exception:
            return {"intents": ["standings"], "week": None, "team_name": None, "player_name": None, "historical": False}

    def _fetch_data(self, intent: dict, question: str) -> dict:
        data = {}
        intents = intent.get("intents", [])
        week = intent.get("week")
        team_name = intent.get("team_name")
        player_name = intent.get("player_name")

        try:
            if "league_info" in intents or not intents:
                data["league_info"] = self.fantasy.get_league_info()

            if "league_settings" in intents:
                data["league_settings"] = self.fantasy.get_league_settings()

            if "standings" in intents:
                data["standings"] = self.fantasy.get_standings()

            if "scoreboard" in intents:
                data["scoreboard"] = self.fantasy.get_scoreboard(week)

            if "matchups" in intents:
                if week:
                    data["matchups"] = self.fantasy.get_matchups_by_week(week)
                else:
                    data["scoreboard"] = self.fantasy.get_scoreboard(None)

            if "teams" in intents:
                data["teams"] = self.fantasy.get_league_teams()

            if "draft" in intents:
                data["draft_results"] = self.fantasy.get_league_draft_results()
                data["teams"] = self.fantasy.get_league_teams()

            if "team_draft" in intents and team_name:
                data["team_draft"] = self.fantasy.get_team_draft_results(team_name)

            if "transactions" in intents:
                data["transactions"] = self.fantasy.get_league_transactions()

            if "roster" in intents and team_name:
                data["roster"] = self.fantasy.get_team_roster(team_name, week)
            elif "roster" in intents:
                data["teams"] = self.fantasy.get_league_teams()

            if "team_stats" in intents and team_name:
                data["team_stats"] = self.fantasy.get_team_stats(team_name, week)

            if "team_matchups" in intents and team_name:
                data["team_matchups"] = self.fantasy.get_team_matchups(team_name)

            if "player_stats" in intents and player_name:
                data["player_stats"] = self.fantasy.get_player_stats(player_name, week)

            if "player_ownership" in intents and player_name:
                data["player_ownership"] = self.fantasy.get_player_ownership(player_name)

            if "players" in intents:
                search = player_name or (question[:30] if len(question) < 50 else None)
                data["players"] = self.fantasy.get_league_players(search)

        except Exception as e:
            logger.error(f"_fetch_data error: {e}")
            data["fetch_error"] = str(e)

        return data

    def _generate_response(self, question: str, data: dict) -> str:
        data_str = json.dumps(data, indent=2, default=str)
        # Truncate if massive (Yahoo returns a LOT of data sometimes)
        if len(data_str) > 12000:
            data_str = data_str[:12000] + "\n... [data truncated]"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"""User question: {question}

League data:
{data_str}

Please answer the question using this data. Be concise and fun!"""
                }
            ]
        )
        return response.content[0].text
