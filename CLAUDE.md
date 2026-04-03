# CS Agent — Zoho SalesIQ AI Customer Support Bot

RomusCasino ve CaptainSlots için Fransız konuşan casino oyuncularına otomatik cevap veren AI bot.
Zoho SalesIQ üzerinde çalışır, bilemediğinde gerçek agente devreder.

## Mimari

```
Müşteri mesaj yazar
    ↓
Zoho SalesIQ Zobot → Deluge script
    ↓
1. Supabase'den ilgili kb_chunks çek (FTS)
2. Zoho API'den conversation history çek
3. Claude API'ye gönder
4. [HANDOFF] varsa agente devret, yoksa cevap ver
```

Deluge script Zoho'nun kendi sunucusunda çalışır — external sunucu yok, deploy yok.

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `1_fetch_transcripts.py` | Zoho API → attended transcript'leri çek → Supabase (transcripts + qa_pairs) |
| `3_build_prompt.py` | Kurallar + davranış → `data/system_prompt.txt` (Q&A örnekleri yok, KB Supabase'den geliyor) |
| `4_generate_deluge.py` | system_prompt → `deluge_final.js` |
| `5_update_kb.py` | Supabase qa_pairs → Claude Haiku → kb_chunks (36 kategori × 2 marka) |
| `deluge_script.js` | Zobot Code Block şablonu |
| `deluge_final.js` | Zobot'a yapıştırılacak final script (sistem promptu gömülü, API key dahil) |
| `.github/workflows/kb_update.yml` | GitHub Actions: günde 2x pipeline |

## Knowledge Base

KB artık `data/knowledge_base/` dosyalarında değil — Supabase `kb_chunks` tablosunda.

**36 alt kategori × 2 marka = 72 chunk:**

| Kategori | Alt kategoriler |
|----------|----------------|
| Bonus (13) | nodep_freespins, survey_spins, birthday, welcome_pack, happy_hour, weekly_promos, activation, wagering, max_cashout, eligible_games, removal, cancellation_rules, loss_request |
| Withdrawal (4) | process, pending, limits, deposit_issue |
| KYC (5) | documents, payment_ownership, process, pending, address_mismatch |
| Account (8) | registration, email_issue, login, phone_geo, duplicate, closure, reactivation, self_exclusion |
| Technical (3) | game, payment, login_issue |
| VIP (3) | how_to_join, cashback, levels |

## Güncelleme Akışı

**Otomatik (GitHub Actions — günde 2x: 12:00 + 20:00 CET):**
1. `1_fetch_transcripts.py` → yeni Zoho transcript'lerini Supabase'e yazar
2. `5_update_kb.py` → kb_chunks'ı günceller

**Deluge script değişince:**
1. `py 3_build_prompt.py`
2. `py 4_generate_deluge.py`
3. `deluge_final.js` → API key ekle → Zobot'a yapıştır → Publish

## Zoho API

- **Region**: EU
- **Base URL**: `https://salesiq.zoho.eu/api/v2/livechathelp247/`
- **Auth**: OAuth 2.0, refresh token (`accounts.zoho.eu`)
- **Conversations**: `GET /conversations?status=attended&limit=99&page=N`
- **Messages**: `GET /conversations/{id}/messages`
- **Scope**: `SalesIQ.conversations.READ`
- **Rate limit**: ~80 req/dk (MIN_INTERVAL=0.75s), 5 paralel thread
- **OAuth console**: `api-console.zoho.eu` (EU hesabı — `.com` değil!)

## Supabase

- **URL**: `https://txkjpwbbperwbbxscxlq.supabase.co`
- **Tablolar**: `transcripts`, `qa_pairs`, `kb_chunks`, `pipeline_state`
- **FTS**: `kb_chunks.search_vector` — French tokenizer, GIN index

## Ortam

- **Python**: `py` komutuyla çalıştır
- **Credentials**: `.env` dosyasında (asla commit etme)
- **Screen name**: `livechathelp247`
- **GitHub repo**: `sarp-rk/cs-agents` (private)

## Markalar

| Brand | Department | Deluge BRAND değeri |
|-------|-----------|---------------------|
| RomusCasino | Romus Department | `romus` |
| CaptainSlots | Captain Department | `captain` |

## Önemli Notlar

- History.csv export'u büyük çoğunlukla **missed** chat — Q&A için işe yaramaz
- Gerçek transcript'ler API ile çekilmeli (`status=attended`)
- `SUPABASE_URL` secret'ında trailing newline olmamalı — `%0a` DNS hatası verir
- Preview modunda handoff = "No proper response" — normal davranış, production'da çalışır
- Deluge'da `urlEncode()` çalışmıyor — `encodeUrl()` kullanılmalı
