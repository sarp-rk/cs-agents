# Slack Conversation Logger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zoho SalesIQ chatbot konuşmaları bittikten sonra Slack'e thread olarak gönder — her bot mesajında hangi KB chunk kullanıldığı görünsün.

**Architecture:** Zoho Workflow `conversation.completed` eventinde VPS'teki Flask endpoint'i çağırır. Endpoint Zoho API'den mesajları, Supabase'den chunk bilgisini çeker, Slack'e thread olarak gönderir. Bot hızı etkilenmez.

**Tech Stack:** Python 3, Flask, Slack Web API (`slack-sdk`), Supabase REST API, Zoho SalesIQ API, Nginx (reverse proxy), PM2

---

## File Structure

| Dosya | Açıklama |
|-------|----------|
| `Create: slack_logger.py` | Flask app — webhook endpoint + Slack gönderme mantığı |
| `Modify: requirements.txt` | `flask`, `slack-sdk` ekle |
| `Modify: .env` | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` ekle |
| `Modify: /etc/nginx/sites-available/chatbotkb.rktechy.com` | `/webhook/conversation-end` → port 5002 |

---

## Ön Koşullar (Manuel Adımlar)

### Slack App Oluşturma
- [ ] **Adım 1:** [api.slack.com/apps](https://api.slack.com/apps) → "Create New App" → "From scratch"
- [ ] **Adım 2:** App name: `CS Bot Logger`, workspace seç
- [ ] **Adım 3:** "OAuth & Permissions" → "Bot Token Scopes" → `chat:write`, `chat:write.public` ekle
- [ ] **Adım 4:** "Install to Workspace" → Bot Token (`xoxb-...`) kopyala
- [ ] **Adım 5:** Hedef kanal oluştur (örn. `#chatbot-logs`) → kanal ID'sini al (kanal adına sağ tık → "Copy link" → URL'deki son segment `C...`)
- [ ] **Adım 6:** Slack app'i o kanala ekle: kanala gir → `/invite @CS Bot Logger`

### VPS .env Güncelleme
- [ ] **Adım 7:** VPS'te `.env` dosyasına ekle:
```bash
ssh root@80.240.17.15
echo 'SLACK_BOT_TOKEN=xoxb-your-token-here' >> /opt/cs-agents/.env
echo 'SLACK_CHANNEL_ID=C0XXXXXXXXX' >> /opt/cs-agents/.env
```

---

## Task 1: Flask App — Temel Webhook Endpoint

**Files:**
- Create: `slack_logger.py`
- Modify: `requirements.txt`

- [ ] **Step 1: `requirements.txt` güncelle**

Dosyaya ekle:
```
flask
slack-sdk
```

- [ ] **Step 2: Temel Flask app yaz**

`slack_logger.py` oluştur:
```python
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
    pass  # implement in next tasks

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
```

- [ ] **Step 3: Local test**

```bash
cd "/d/OneDrive/AI/Rkgametech/CS Agents"
py -c "import flask, slack_sdk; print('deps ok')"
```
Expected: `deps ok`

- [ ] **Step 4: HEAD request test (Zoho webhook validation)**

Başka terminalde:
```bash
py slack_logger.py &
curl -I http://localhost:5002/webhook/conversation-end
```
Expected: `HTTP/1.1 200 OK`

- [ ] **Step 5: Commit**

```bash
git add slack_logger.py requirements.txt
git commit -m "feat(slack): Flask webhook skeleton with HEAD validation"
```

---

## Task 2: Supabase'den KB Log Çekme

**Files:**
- Modify: `slack_logger.py`

- [ ] **Step 1: `get_kb_logs` fonksiyonu yaz**

`slack_logger.py`'e ekle (process_conversation'dan önce):
```python
import requests as req

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
```

- [ ] **Step 2: Test ile doğrula**

```bash
py -c "
from slack_logger import get_kb_logs
rows = get_kb_logs('114474000002823105')
print(len(rows), 'rows')
if rows: print(rows[0].keys())
"
```
Expected: `N rows` ve `dict_keys(['customer_message', 'bot_reply', 'chunks_used', 'source_tag'])`

- [ ] **Step 3: Commit**

```bash
git add slack_logger.py
git commit -m "feat(slack): fetch kb_logs from Supabase by conv_id"
```

---

## Task 3: Zoho API'den Konuşma Mesajlarını Çekme

**Files:**
- Modify: `slack_logger.py`

- [ ] **Step 1: Zoho access token fonksiyonu yaz**

```python
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
```

- [ ] **Step 2: `get_zoho_messages` fonksiyonu yaz**

```python
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
    # Kronolojik sırala (en eski önce)
    return sorted(data, key=lambda m: m.get("time", 0))
```

- [ ] **Step 3: Test**

```bash
py -c "
from slack_logger import get_zoho_messages
msgs = get_zoho_messages('114474000002823105')
print(len(msgs), 'messages')
for m in msgs[:3]:
    sender = m.get('sender', {}).get('type', '?')
    text = m.get('message', {}).get('text', '')[:60]
    print(f'  {sender}: {text}')
"
```
Expected: Mesaj listesi visitor/bot/operator sırasıyla

- [ ] **Step 4: Commit**

```bash
git add slack_logger.py
git commit -m "feat(slack): fetch Zoho conversation messages"
```

---

## Task 4: Slack'e Thread Gönderme

**Files:**
- Modify: `slack_logger.py`

- [ ] **Step 1: Slack client ekle ve format fonksiyonu yaz**

`import`'lara ekle:
```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
```

Slack format fonksiyonlarını ekle:
```python
def slack_client():
    return WebClient(token=SLACK_BOT_TOKEN)

def format_chunks(chunks_used):
    """chunks_used JSON listesinden okunabilir string üret."""
    if not chunks_used:
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
```

- [ ] **Step 2: `send_to_slack` fonksiyonu yaz**

```python
def send_to_slack(conv_id, brand, zoho_data, zoho_msgs, kb_logs):
    """Konuşmayı Slack'e thread olarak gönder."""
    client = slack_client()
    
    # kb_logs'u customer_message'a göre index'le
    kb_index = {}
    for row in kb_logs:
        key = (row.get("customer_message") or "").strip()
        kb_index[key] = row

    # Visitor bilgisi
    visitor = zoho_data.get("visitor", {})
    visitor_name = visitor.get("name") or zoho_data.get("visitor_name") or "Visitor"
    duration_ms = zoho_data.get("duration") or zoho_data.get("duration_ms")
    duration_str = f" | ⏱ {format_duration(duration_ms)}" if duration_ms else ""

    # Ana mesaj
    header = f"📩 *Yeni Konuşma* | `{brand}` | Conv `{conv_id[-8:]}`\n👤 {visitor_name}{duration_str}"
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
        text = msg.get("message", {}).get("text", "")
        if not text or text.strip() == "":
            continue

        if sender == "visitor":
            prev_visitor_text = text.strip()
            slack_text = f"👤  {text}"
        elif sender in ("bot", "operator", "agent"):
            kb = kb_index.get(prev_visitor_text or "")
            chunk_str = format_chunks(kb.get("chunks_used") if kb else None)
            source = kb.get("source_tag", "") if kb else ""
            source_str = f"\n🏷️  `{source}`" if source else ""
            chunk_line = f"\n{chunk_str}" if chunk_str else ""
            slack_text = f"🤖  {text}{chunk_line}{source_str}"
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
                text=f"↗️  *Transfer edildi* → {transferred_to}",
                thread_ts=thread_ts,
            )
        except SlackApiError as e:
            log.error(f"Slack transfer post failed: {e}")
```

- [ ] **Step 3: `process_conversation` fonksiyonunu tamamla**

`pass` satırını şununla değiştir:
```python
def process_conversation(conv_id, brand, zoho_data):
    zoho_msgs = get_zoho_messages(conv_id)
    kb_logs = get_kb_logs(conv_id)
    log.info(f"Conv {conv_id}: {len(zoho_msgs)} msgs, {len(kb_logs)} kb_logs")
    send_to_slack(conv_id, brand, zoho_data, zoho_msgs, kb_logs)
    log.info(f"Conv {conv_id}: sent to Slack")
```

- [ ] **Step 4: Manuel test**

```bash
py -c "
from slack_logger import process_conversation
process_conversation('114474000002823105', 'captain', {'visitor_name': 'Test User'})
print('Done — check Slack')
"
```
Expected: Slack kanalında yeni thread

- [ ] **Step 5: Commit**

```bash
git add slack_logger.py
git commit -m "feat(slack): send conversation thread to Slack with chunk info"
```

---

## Task 5: VPS Deploy

**Files:**
- Modify: `/etc/nginx/sites-available/chatbotkb.rktechy.com` (VPS'te)
- Modify: `/opt/cs-agents/requirements.txt` (VPS'te)

- [ ] **Step 1: Kodu VPS'e push et**

```bash
git push origin main
```

- [ ] **Step 2: VPS'te kur**

```bash
ssh root@80.240.17.15 "
cd /opt/cs-agents &&
git pull &&
venv/bin/pip install flask slack-sdk &&
echo 'flask' >> requirements.txt &&
echo 'slack-sdk' >> requirements.txt
"
```

- [ ] **Step 3: PM2 ile başlat**

```bash
ssh root@80.240.17.15 "
cd /opt/cs-agents &&
pm2 start 'venv/bin/python slack_logger.py' --name slack-logger &&
pm2 save
"
```
Expected: `pm2 list` → `slack-logger` online

- [ ] **Step 4: Nginx'e webhook location ekle**

```bash
ssh root@80.240.17.15 "
cat >> /etc/nginx/sites-available/chatbotkb.rktechy.com << 'NGINX'

    location /webhook/ {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
NGINX
"
```

**Not:** Bu komutu çalıştırmadan önce mevcut dosyayı görüntüle — SSL server block'un **içine** eklenmeli (kapanış `}` öncesi). Gerekirse manuel düzenle:
```bash
ssh root@80.240.17.15 "nano /etc/nginx/sites-available/chatbotkb.rktechy.com"
```

- [ ] **Step 5: Nginx test ve reload**

```bash
ssh root@80.240.17.15 "nginx -t && systemctl reload nginx"
```
Expected: `nginx: configuration file ... syntax is ok`

- [ ] **Step 6: HTTPS endpoint test**

```bash
curl -I https://chatbotkb.rktechy.com/webhook/conversation-end
```
Expected: `HTTP/2 200`

- [ ] **Step 7: Commit**

```bash
git add requirements.txt
git commit -m "feat(slack): VPS deploy — Flask on port 5002, nginx /webhook/ route"
```

---

## Task 6: Zoho Workflow Kurulumu (Manuel)

- [ ] **Step 1:** Zoho SalesIQ → Settings → **Automation** → **Workflows** → "New Workflow"
- [ ] **Step 2:** Name: `Slack Conversation Logger`
- [ ] **Step 3:** Module: `Conversations` → Event: `conversation.completed`
- [ ] **Step 4:** Conditions: (yok — tüm konuşmalar)
- [ ] **Step 5:** Action: **Webhook**
  - URL: `https://chatbotkb.rktechy.com/webhook/conversation-end`
  - Method: POST
  - Content-Type: application/json
  - Body (raw JSON):
  ```json
  {
    "conv_id": "${conversation.id}",
    "brand": "${conversation.department}",
    "visitor_name": "${visitor.name}",
    "duration": "${conversation.duration}",
    "attender": "${conversation.attender.name}"
  }
  ```
  **Not:** Zoho'nun field syntax'ı `${field}` şeklinde değil farklı olabilir — Zoho UI'da "Insert Variable" butonunu kullan.
- [ ] **Step 6:** Save → Enable
- [ ] **Step 7:** Test: Bir konuşmayı manuel kapat → Slack'i kontrol et

---

## Task 7: Hata İzleme — Telegram Bildirimi

**Files:**
- Modify: `slack_logger.py`

- [ ] **Step 1: Telegram hata fonksiyonu ekle**

`slack_logger.py`'e ekle:
```python
TELEGRAM_BOT_TOKEN = "8697477909:AAHleRugZFFifdMA3aVSY53EaBZ0o-v1B3I"
TELEGRAM_CHAT_ID = "-5151563452"

def notify_telegram(message):
    try:
        req.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=5,
        )
    except Exception:
        pass
```

- [ ] **Step 2: `process_conversation` except bloğunu güncelle**

Webhook handler'daki `except Exception as e:` bloğunu şununla değiştir:
```python
    except Exception as e:
        log.error(f"Error processing {conv_id}: {e}")
        notify_telegram(f"[Slack Logger ERROR] conv_id={conv_id} | {e}")
```

- [ ] **Step 3: Commit ve deploy**

```bash
git add slack_logger.py
git commit -m "feat(slack): Telegram error notifications"
git push origin main
ssh root@80.240.17.15 "cd /opt/cs-agents && git pull && pm2 restart slack-logger"
```

---

## Test Senaryoları

| Senaryo | Beklenen |
|---------|----------|
| Normal konuşma (bot cevap + chunk) | Thread açılır, her mesaj reply, chunk görünür |
| Transfer olan konuşma | Son reply "↗️ Transfer edildi → agent adı" |
| KB bilgisi olmayan konuşma | Thread açılır, chunk satırı boş |
| Zoho API erişim hatası | Telegram'a hata bildirimi, Slack'e mesaj gitmez |
| Slack token geçersiz | Telegram'a hata bildirimi, log'a kayıt |

---
*Plan tarihi: 2026-05-19*
