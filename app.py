import os
import json
import logging
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from fantasy import YahooFantasyClient
from ai import FantasyAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("FB_VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
APP_SECRET = os.environ.get("FB_APP_SECRET")

fantasy_client = YahooFantasyClient()
ai = FantasyAI(fantasy_client)


def verify_signature(payload, signature):
    """Verify that the request actually came from Facebook."""
    if not signature:
        return False
    sha_name, sig = signature.split("=", 1)
    if sha_name != "sha256":
        return False
    mac = hmac.new(APP_SECRET.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig)


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Facebook webhook verification handshake."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully!")
        return challenge, 200
    else:
        logger.warning("Webhook verification failed.")
        return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming messages from Facebook Messenger."""
    # Verify the request signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.data, signature):
        logger.warning("Invalid signature, rejecting request.")
        return "Unauthorized", 401

    data = request.get_json()
    logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event.get("sender", {}).get("id")
                message = event.get("message", {})
                text = message.get("text", "")

                if text and sender_id:
                    # Don't respond to the page's own messages
                    if sender_id == os.environ.get("FB_PAGE_ID"):
                        continue
                    handle_message(sender_id, text)

    return "OK", 200


def handle_message(sender_id: str, text: str):
    """Process incoming message and send a response."""
    logger.info(f"Handling message from {sender_id}: {text}")

    try:
        # Show typing indicator
        send_action(sender_id, "typing_on")

        # Get AI response
        response = ai.answer(text)

        # Send response
        send_message(sender_id, response)

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        send_message(
            sender_id,
            "Sorry, I ran into an error fetching your fantasy data. Please try again!"
        )


def send_message(recipient_id: str, text: str):
    """Send a text message via the Messenger Send API."""
    # Messenger has a 2000 char limit per message
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    for chunk in chunks:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": chunk},
            "messaging_type": "RESPONSE"
        }
        response = requests.post(
            f"https://graph.facebook.com/v19.0/me/messages",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json=payload
        )
        if response.status_code != 200:
            logger.error(f"Failed to send message: {response.text}")


def send_action(recipient_id: str, action: str):
    """Send a sender action (e.g. typing indicator)."""
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": action
    }
    requests.post(
        f"https://graph.facebook.com/v19.0/me/messages",
        params={"access_token": PAGE_ACCESS_TOKEN},
        json=payload
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
