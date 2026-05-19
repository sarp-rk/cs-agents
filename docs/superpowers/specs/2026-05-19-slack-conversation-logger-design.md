# Slack Conversation Logger — Design Spec

## Goal

Zoho SalesIQ chatbot konuşmaları bittikten sonra Slack'e thread olarak gönder. Her bot mesajının hangi KB chunk'ından üretildiği görünür olsun. Bot hızı etkilenmesin.

## Architecture

```
Zoho SalesIQ
  conversation.completed event
      ↓
  Workflow → POST /webhook/conversation-end (VPS)
      ↓
  VPS endpoint (Python Flask)
    1. Zoho API → konuşma mesajlarını çek
    2. Supabase kb_logs → conv_id'ye ait chunk bilgilerini çek
    3. Slack API → ana mesaj gönder (thread açılır)
    4. Slack API → her mesaj çifti için thread reply gönder
      ↓
  Slack channel
    📩 Konuşma başlığı [ana mesaj]
      └─ 👤 Müşteri mesajı
      └─ 🤖 Bot cevabı | [chunk: withdrawal_pending, sim: 0.82]
      └─ 👤 Müşteri mesajı
      └─ 🤖 Bot cevabı | [chunk: withdrawal_limits, sim: 0.71]
      └─ ↗️ Transfer edildi  (varsa)
```

## Components

### 1. Zoho Workflow (Zoho panelinden kurulur)
- Trigger: `conversation.completed`
- Action: Webhook → `POST https://80.240.17.15/webhook/conversation-end`
- Payload: `conv_id`, `brand`, `visitor_name`, `duration_ms`, `operator` (transfer varsa)

### 2. VPS Endpoint — `/webhook/conversation-end`
**Dosya:** `/opt/cs-agents/slack_logger.py`
**Framework:** Flask (zaten kurulu)
**Port:** Nginx reverse proxy üzerinden

Akış:
1. Zoho payload'ından `conv_id` ve `brand` al
2. Zoho API → `GET /conversations/{conv_id}/messages` → mesaj listesi
3. Supabase → `kb_logs` tablosundan `conv_id`'ye ait tüm satırları çek (customer_message, bot_reply, chunks_used, source_tag)
4. Mesajları birleştir: Zoho'dan visitor mesajları, Supabase'den bot cevapları + chunk bilgisi
5. Slack API → `chat.postMessage` → ana thread mesajı
6. Her mesaj çifti için `chat.postMessage` → `thread_ts` ile reply

### 3. Slack Mesaj Formatı

**Ana mesaj:**
```
📩 *Yeni Konuşma* | captain | Conv #114474...
👤 Müşteri: Jean Dupont | ⏱ 4 dk 23 sn
```

**Thread reply — müşteri mesajı:**
```
👤  Je veux retirer mon argent
```

**Thread reply — bot cevabı:**
```
🤖  Votre retrait est en cours de traitement...
📎  [withdrawal_pending | sim: 0.82]  [withdrawal_limits | sim: 0.71]
🏷️  source: kb
```

**Thread reply — transfer (varsa):**
```
↗️  *Transfer edildi* → Allen | Customer Success
```

### 4. Supabase — kb_logs tablosu (mevcut)

```sql
conv_id        text
customer_message text
bot_reply      text
chunks_used    jsonb  -- [{"category": "withdrawal_pending", "similarity": 0.82}, ...]
source_tag     text   -- "kb" | "prompt_rules" | "transfer" | "hallucination_risk"
```

Bu tablo Deluge script tarafından her bot cevabında zaten dolduruluyor.

## Data Flow Detayı

```
Zoho Workflow → POST /webhook/conversation-end
  {conv_id, brand, visitor_name, duration_ms}
      ↓
Flask endpoint:
  zoho_msgs = zoho_api.get_messages(conv_id)  # tüm mesajlar
  kb_rows   = supabase.get_kb_logs(conv_id)   # bot cevapları + chunks
  
  # kb_rows'u customer_message'a göre index'le
  kb_index = {row.customer_message: row for row in kb_rows}
  
  # Slack'e gönder
  resp = slack.post_message(channel, header_text)
  thread_ts = resp["ts"]
  
  for msg in zoho_msgs:
    if msg.sender == "visitor":
      slack.post_reply(thread_ts, f"👤 {msg.text}")
    elif msg.sender in ("bot", "operator"):
      kb = kb_index.get(prev_visitor_msg)
      chunk_text = format_chunks(kb.chunks_used) if kb else ""
      slack.post_reply(thread_ts, f"🤖 {msg.text}\n{chunk_text}")
```

## VPS Setup

- Yeni script: `/opt/cs-agents/slack_logger.py`
- Nginx config: `/etc/nginx/sites-available/cs-agents` → `/webhook/conversation-end` → Flask port
- PM2: `slack-logger` process olarak çalışır
- Secrets: `.env` dosyasına `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` eklenir

## Slack Setup

- Slack App oluştur → `chat:write` permission
- Bot token (`xoxb-...`) al
- Hedef kanal ID'si belirle (örn. `#chatbot-logs`)

## Error Handling

- Zoho API hata verirse: Slack'e "API error" thread açılmaz, Telegram'a hata gönderilir
- Supabase hata verirse: Chunk bilgisi olmadan mesajlar gönderilir
- Slack API hata verirse: Telegram'a bildirim

## Out of Scope

- Konuşma içinde gerçek zamanlı Slack güncellemesi (sadece bittikten sonra)
- Slack'ten aksiyon alma
- Birden fazla Slack kanalı (tek kanal, her iki marka)

---
*Spec tarihi: 2026-05-19*
