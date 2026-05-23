import os
import logging
import requests as req
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import anthropic

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ZOHO_SCREEN_NAME = os.getenv("ZOHO_SCREEN_NAME", "livechathelp247")
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ZOHO_ACCOUNTS_URL = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.eu")

def get_zoho_token():
    resp = req.post(f"{ZOHO_ACCOUNTS_URL}/oauth/v2/token", data={
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }, timeout=10)
    return resp.json()["access_token"]

def get_zoho_messages(conv_id):
    """Zoho API'den konuşma mesajlarını çek, kronolojik sırayla döndür."""
    try:
        token = get_zoho_token()
    except Exception as e:
        log.error(f"Zoho token error: {e}")
        return []
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    resp = req.get(
        f"https://salesiq.zoho.eu/api/v2/{ZOHO_SCREEN_NAME}/conversations/{conv_id}/messages",
        params={"limit": 50},
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        log.warning(f"Zoho messages fetch failed: {resp.status_code}")
        return []
    data = resp.json().get("data", [])
    return sorted(data, key=lambda m: m.get("time", 0))

@app.route("/webhook/conversation-end", methods=["HEAD", "POST"])
def conversation_end():
    if request.method == "HEAD":
        return "", 200
    data = request.json or {}
    log.info(f"Webhook received: {data}")
    conv_id = (
        data.get("conv_id")
        or data.get("entity_id")
        or data.get("id")
        or data.get("conversation", {}).get("id")
        or (data.get("entity") or {}).get("id")
    )
    DEPT_BRAND_MAP = {
        "114474000001615143": "captain",
        "114474000002303023": "romus",
    }
    dept_id = (data.get("entity") or {}).get("department_id", "")
    dept = (data.get("department") or {}).get("name", "") or data.get("department_name", "")
    if dept_id in DEPT_BRAND_MAP:
        brand = DEPT_BRAND_MAP[dept_id]
    elif "captain" in dept.lower():
        brand = "captain"
    elif "romus" in dept.lower():
        brand = "romus"
    else:
        brand = data.get("brand", dept or "unknown")
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

_anthropic_client = None

def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _anthropic_client

def translate_to_english(text):
    """Translate text to English using Claude Haiku. Returns original on failure."""
    if not text or not text.strip():
        return text
    try:
        client = get_anthropic_client()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"Translate the following text to English. Return ONLY the translation, no explanations:\n\n{text}"
            }]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.warning(f"Translation failed: {e}")
        return text

def slack_client():
    return WebClient(token=SLACK_BOT_TOKEN)

def format_chunks(chunks_used):
    """chunks_used JSON listesinden okunabilir string üret."""
    if not chunks_used:
        return ""
    import json
    if isinstance(chunks_used, str):
        try:
            chunks_used = json.loads(chunks_used)
        except Exception:
            return ""
    parts = []
    for c in chunks_used:
        cat = c.get("category", "?")
        sim = c.get("similarity", 0)
        parts.append(f"`{cat}` {sim:.2f}")
    return "📎 " + " · ".join(parts)

def format_duration(duration_ms):
    if not duration_ms:
        return ""
    secs = int(duration_ms) // 1000
    return f"{secs // 60}m {secs % 60}s"

def send_to_slack(conv_id, brand, zoho_data, zoho_msgs, kb_logs):
    """Konuşmayı Slack'e thread olarak gönder."""
    client = slack_client()

    # kb_logs'u customer_message'a göre index'le
    kb_index = {}
    for row in kb_logs:
        key = (row.get("customer_message") or "").strip()
        kb_index[key] = row

    # Visitor bilgisi
    entity = zoho_data.get("entity", {})
    visitor = entity.get("visitor") or zoho_data.get("visitor") or {}
    visitor_name = visitor.get("name") or zoho_data.get("visitor_name") or "Visitor"
    duration_ms = zoho_data.get("duration") or zoho_data.get("duration_ms") or (
        (int(entity.get("end_time", 0)) - int(entity.get("opened_time", 0))) if entity.get("end_time") and entity.get("opened_time") else None
    )
    duration_str = f" | ⏱ {format_duration(duration_ms)}" if duration_ms else ""
    ref_id = entity.get("reference_id") or ""
    ref_str = f" | #{ref_id}" if ref_id else ""

    # Ana mesaj
    header = f"📩 *New Conversation* | `{brand}` | Conv `{conv_id[-8:]}`{ref_str}\n👤 {visitor_name}{duration_str}"
    try:
        resp = client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=header)
        thread_ts = resp["ts"]
    except SlackApiError as e:
        log.error(f"Slack header post failed: {e}")
        return

    # Thread reply'ları
    prev_visitor_text = None
    for msg in zoho_msgs:
        sender = msg.get("sender", {}).get("type", "")
        from html import unescape
        text = unescape((msg.get("message") or {}).get("text", ""))
        if not text or not text.strip():
            continue

        if sender == "visitor":
            prev_visitor_text = text.strip()
            slack_text = f"👤  {translate_to_english(text)}"
        elif sender in ("bot", "operator", "agent"):
            kb = kb_index.get(prev_visitor_text or "")
            chunk_str = format_chunks(kb.get("chunks_used") if kb else None)
            source = kb.get("source_tag", "") if kb else ""
            source_str = f"\n🏷️  `{source}`" if source else ""
            chunk_line = f"\n{chunk_str}" if chunk_str else ""
            slack_text = f"🤖  {translate_to_english(text)}{chunk_line}{source_str}"
            prev_visitor_text = None
        else:
            continue

        try:
            client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=slack_text, thread_ts=thread_ts)
        except SlackApiError as e:
            log.error(f"Slack reply post failed: {e}")

    # Transfer varsa son satır
    transferred_to = zoho_data.get("attender", {}).get("name") or zoho_data.get("operator")
    if transferred_to:
        try:
            client.chat_postMessage(
                channel=SLACK_CHANNEL_ID,
                text=f"↗️  *Transferred* → {transferred_to}",
                thread_ts=thread_ts,
            )
        except SlackApiError as e:
            log.error(f"Slack transfer post failed: {e}")

def process_conversation(conv_id, brand, zoho_data):
    zoho_msgs = get_zoho_messages(conv_id)
    kb_logs = get_kb_logs(conv_id)
    log.info(f"Conv {conv_id}: {len(zoho_msgs)} msgs, {len(kb_logs)} kb_logs")
    send_to_slack(conv_id, brand, zoho_data, zoho_msgs, kb_logs)
    log.info(f"Conv {conv_id}: sent to Slack")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)

