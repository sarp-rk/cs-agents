# Project Overview — CS Agents

## Mimari
Müşteri mesajı → Zoho SalesIQ Zobot → Deluge script:
1. Supabase'den ilgili kb_chunks çek (vector search)
2. Zoho API'den conversation history çek (limit: 20 mesaj)
3. Claude API'ye gönder (claude-haiku-4-5-20251001)
4. [HANDOFF] varsa agente devret, yoksa cevap ver

External sunucu yok — Deluge Zoho'nun kendi sunucusunda çalışır.

## Önemli Dosyalar
| Dosya | Açıklama |
|-------|----------|
| `deluge_final.js` | Zobot'a yapıştırılacak script (API key manuel eklenir) |
| `deluge_script.js` | Şablon |
| `data/system_prompt.txt` | Aktif system prompt |
| `data/system_prompt_v1_backup.txt` | Orijinal prompt (~629 token) |
| `data/system_prompt_v2.txt` | Optimize prompt (~220 token) |
| `1_fetch_transcripts.py` | Zoho → Supabase transcript çekme |
| `5_update_kb.py` | kb_chunks güncelleme |
| `3_build_prompt.py` | system_prompt.txt üretir |
| `4_generate_deluge.py` | deluge_final.js üretir |
| `test_bot.py` | Claude API direkt test (Zoho bypass) |

## Deluge Script Güncelleme Adımları
1. `py 3_build_prompt.py`
2. `py 4_generate_deluge.py`
3. `deluge_final.js` → API key ekle → Zobot'a yapıştır → Publish

## Credentials (.env)
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL` / `SUPABASE_KEY`
- `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` / `ZOHO_REFRESH_TOKEN`
- `.env` asla commit edilmez

## Supabase
- URL: `https://txkjpwbbperwbbxscxlq.supabase.co`
- Tablolar: `transcripts`, `qa_pairs`, `kb_chunks`, `pipeline_state`
- FTS: `kb_chunks.search_vector` — French tokenizer

## Markalar
| Brand | Deluge BRAND değeri |
|-------|---------------------|
| RomusCasino | `romus` |
| CaptainSlots | `captain` |

## Token Optimizasyonu (2026-04-03)
- Problem: Input token ~2500/mesaj
- v1 base prompt: ~629 token
- v2 base prompt: ~220 token (%65 azalma)
- Test: Zobot'ta v1 → v2 geçişi yapıp aynı soruları sor, Anthropic Console'dan karşılaştır

## Önemli Notlar
- Deluge'da `encodeUrl()` kullan, `urlEncode()` çalışmıyor
- `SUPABASE_URL` secret'ında trailing newline olmamalı (`%0a` DNS hatası verir)
- Preview modunda handoff = "No proper response" — normal, production'da çalışır
- Zoho OAuth: EU hesabı → `accounts.zoho.eu` (`.com` değil)
- GitHub Actions: günde 2x (12:00 + 20:00 CET) pipeline çalışır
