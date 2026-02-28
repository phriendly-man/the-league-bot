import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FantasyBot, an expert fantasy football assistant for a private Yahoo Fantasy Football league. 
You have access to live league data and can answer questions about standings, scores, rosters, players, and matchups.

Your personality:
- Fun, witty, and trash-talk friendly (this is a friend group!)
- Use football lingo naturally
- Keep responses concise but informative
- Add light humor when appropriate
- Use emojis sparingly but effectively 🏈

When you receive league data alongside a question, use it to give accurate, specific answers.
When data has an "error" field, apologize and explain the data couldn't be fetched.

Format guidelines:
- Use clear line breaks for readability
- For standings/scores, use simple text tables or ranked lists
- Keep responses under 1500 characters when possible (Messenger limit awareness)
- If a question is ambiguous, answer the most likely interpretation

You are NOT able to give betting advice or predict game outcomes with certainty."""


class FantasyAI:
    def __init__(self, fantasy_client):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.fantasy = fantasy_client
        self.model = "claude-opus-4-6"

    def answer(self, question: str) -> str:
        """
        Given a natural language question, fetch relevant data and return a response.
        Uses Claude to both understand the question AND generate the response.
        """
        # Step 1: Use Claude to figure out what data we need
        intent = self._classify_intent(question)
        logger.info(f"Classified intent: {intent}")

        # Step 2: Fetch the relevant data
        context_data = self._fetch_data(intent, question)

        # Step 3: Use Claude to generate a natural language response
        return self._generate_response(question, context_data)

    def _classify_intent(self, question: str) -> dict:
        """Use Claude to determine what fantasy data is needed to answer the question."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system="""You are a fantasy football query classifier. Given a user question, return a JSON object with:
- "intents": list of data types needed from: ["standings", "scoreboard", "teams", "roster", "player_stats", "transactions", "league_info"]
- "week": specific week number if mentioned (null if current week or not applicable)  
- "team_name": team name if specifically mentioned (null otherwise)
- "player_name": player name if specifically mentioned (null otherwise)

Respond ONLY with valid JSON, no other text.""",
            messages=[{"role": "user", "content": question}]
        )

        try:
            return json.loads(response.content[0].text)
        except Exception:
            # Default to fetching standings and scoreboard
            return {"intents": ["standings", "scoreboard"], "week": None, "team_name": None, "player_name": None}

    def _fetch_data(self, intent: dict, question: str) -> dict:
        """Fetch all relevant data based on the classified intent."""
        data = {}
        intents = intent.get("intents", [])
        week = intent.get("week")
        team_name = intent.get("team_name")
        player_name = intent.get("player_name")

        if "league_info" in intents or not intents:
            data["league_info"] = self.fantasy.get_league_info()

        if "standings" in intents:
            data["standings"] = self.fantasy.get_standings()

        if "scoreboard" in intents:
            data["scoreboard"] = self.fantasy.get_scoreboard(week)

        if "teams" in intents:
            data["teams"] = self.fantasy.get_league_teams()

        if "roster" in intents and team_name:
            data["roster"] = self.fantasy.get_team_roster(team_name)
        elif "roster" in intents:
            data["teams"] = self.fantasy.get_league_teams()

        if "player_stats" in intents and player_name:
            data["player_stats"] = self.fantasy.get_player_stats(player_name, week)

        if "transactions" in intents:
            data["transactions"] = self.fantasy.get_league_transactions()

        return data

    def _generate_response(self, question: str, data: dict) -> str:
        """Use Claude to generate a natural language response from the data."""
        data_str = json.dumps(data, indent=2, default=str)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
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
