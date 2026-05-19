import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ZOHO_SCREEN_NAME = os.getenv("ZOHO_SCREEN_NAME", "livechathelp247")

@app.route("/webhook/conversation-end", methods=["HEAD", "POST"])
def conversation_end():
    if request.method == "HEAD":
        return "", 200
    data = request.json or {}
    log.info(f"Webhook received: {data}")
    conv_id = data.get("conv_id") or data.get("conversation", {}).get("id")
    brand = data.get("brand", "unknown")
    if not conv_id:
        log.warning("No conv_id in payload")
        return jsonify({"error": "no conv_id"}), 400
    try:
        process_conversation(conv_id, brand, data)
    except Exception as e:
        log.error(f"Error processing {conv_id}: {e}")
    return jsonify({"ok": True}), 200

def process_conversation(conv_id, brand, zoho_data):
    pass  # implemented in later tasks

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
