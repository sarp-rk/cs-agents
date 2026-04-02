# CS Agent — Zoho SalesIQ AI Customer Support Bot

RomusCasino ve CaptainSlots için Fransız konuşan casino oyuncularına otomatik cevap veren AI bot.
Zoho SalesIQ üzerinde çalışır, bilemediğinde gerçek agente devreder.

## Mimari

```
Müşteri mesaj yazar → Zoho SalesIQ Zobot → Deluge script (Claude API çağrısı) → Cevap
Bilmiyorsa → gerçek agente devreder
```

Deluge script Zoho'nun kendi sunucusunda çalışır — external sunucu yok, deploy yok.

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `1_fetch_transcripts.py` | Zoho API → attended chat transcript'leri çek → `data/transcripts/` |
| `2_process_data.py` | Transcript'lerden Q&A çiftleri çıkar → `data/qa_pairs.jsonl` |
| `3_build_prompt.py` | KB + Q&A örneklerini birleştirip sistem promptu oluşturur → `data/system_prompt.txt` |
| `4_generate_deluge.py` | Sistem promptunu `deluge_script.js` şablonuna gömer → `deluge_final.js` |
| `deluge_script.js` | Zobot Code Block şablonu (Claude API çağrısı, handoff logic) |
| `deluge_final.js` | Zobot'a yapıştırılacak final script (sistem promptu gömülü) |
| `data/knowledge_base/` | KB dosyaları (.md) |
| `data/qa_pairs.jsonl` | Transcript'lerden çıkarılan Q&A çiftleri |

## Knowledge Base

| Dosya | İçerik | Durum |
|-------|--------|-------|
| `romuscasino_promotions.md` | Tüm bonus detayları (Welcome Pack, Happy Hour, vb.) | ✅ Hazır |
| `romuscasino_terms.md` | T&C, KYC, çekim limitleri | ✅ Hazır |
| `romuscasino_bonus_terms.md` | Max cashout, wagering kuralları | ✅ Hazır |
| `captainslots_*.md` | CaptainSlots için aynıları | ⏳ Bekliyor |
| `manual_qa.md` | Ekip tarafından yazılacak sık sorular | ⏳ Bekliyor |

## Güncelleme Akışı

KB değişince:
1. `data/knowledge_base/` dosyasını güncelle
2. `py 3_build_prompt.py`
3. `py 4_generate_deluge.py`
4. `deluge_final.js` → API key ekle → Zobot'a yapıştır → Publish

## Zoho API

- **Region**: EU
- **Base URL**: `https://salesiq.zoho.eu/api/v2/livechathelp247/`
- **Auth**: OAuth 2.0, refresh token (`accounts.zoho.eu`)
- **Conversations**: `GET /conversations?status=attended&limit=99&page=N`
- **Messages**: `GET /conversations/{id}/messages`
- **Scope**: `SalesIQ.conversations.READ`
- **Rate limit**: ~80 req/dk (MIN_INTERVAL=0.75s), 5 paralel thread
- **OAuth console**: `api-console.zoho.eu` (EU hesabı — `.com` değil!)

## Ortam

- **Python**: `py` komutuyla çalıştır
- **Credentials**: `.env` dosyasında (asla commit etme)
- **Screen name**: `livechathelp247`

## Markalar

| Brand | Department |
|-------|-----------|
| RomusCasino | Romus Department |
| CaptainSlots | Captain Department |

## Önemli Notlar

- History.csv export'u büyük çoğunlukla **missed** chat — agent yanıtı yok, Q&A için işe yaramaz
- Gerçek transcript'ler API ile çekilmeli (`status=attended`)
- CaptainSlots sitesi Cloudflare korumalı — manuel kopyalama gerekiyor
- `4_generate_deluge.py` Unicode filtresi: emoji ve U+024F üstü karakterleri temizler (Deluge parser sorunu)
- Preview modunda handoff = "No proper response" — normal davranış, production'da çalışır
