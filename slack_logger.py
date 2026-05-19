import os
import logging
import requests as req
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

def get_kb_logs(conv_id):
    """Supabase kb_logs tablosundan conv_id'ye ait tüm satırları çek."""
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }
    resp = req.get(
        f"{SUPABASE_URL}/rest/v1/kb_logs",
        params={"conv_id": f"eq.{conv_id}", "select": "customer_message,bot_reply,chunks_used,source_tag"},
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        log.warning(f"kb_logs fetch failed: {resp.status_code} {resp.text[:200]}")
        return []
    return resp.json()

def process_conversation(conv_id, brand, zoho_data):
    pass  # implemented in later tasks

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
