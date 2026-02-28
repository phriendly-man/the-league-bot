"""
Test your bot locally without Facebook.
Run this to make sure your Yahoo + Claude integration works before deploying.

Usage:
  python test_bot.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("🏈 Fantasy Bot Local Tester")
    print("=" * 40)
    print("Type a question to test your bot.")
    print("Type 'quit' to exit.")
    print()

    # Check env vars
    required = ["YAHOO_CLIENT_ID", "YAHOO_CLIENT_SECRET", "YAHOO_LEAGUE_ID", "ANTHROPIC_API_KEY"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Make sure your .env file is set up correctly.")
        return

    from fantasy import YahooFantasyClient
    from ai import FantasyAI

    print("Initializing Yahoo Fantasy client...")
    fantasy = YahooFantasyClient()
    ai = FantasyAI(fantasy)
    print("✅ Ready!\n")

    while True:
        try:
            question = input("You: ").strip()
            if question.lower() in ("quit", "exit", "q"):
                break
            if not question:
                continue

            print("Bot: thinking...")
            response = ai.answer(question)
            print(f"Bot: {response}")
            print()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
