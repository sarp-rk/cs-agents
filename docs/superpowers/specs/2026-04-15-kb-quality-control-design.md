# KB Quality Control — Design Spec
**Date:** 2026-04-15  
**Project:** CS Agents (RomusCasino / CaptainSlots)

## Problem

Bot müşterilere yanlış bilgi verebiliyor. Kök neden: `5_update_kb.py` agent konuşmalarından otomatik öğreniyor — eski tarihli, affiliate kampanyasına özel, ya da agent'ın manuel yaptığı one-off işlemleri genel politikaymış gibi KB'ye giriyor.

Örnek: Haziran 2024'teki Ruby Vegas affiliate kampanyasındaki "30 free spins on Gates of Olympus" konuşmaları, mevcut bir politika gibi KB chunk'ına dönüştü ve bot bunu müşterilere sundu.

## Çözüm: 3 Katmanlı Kalite Kontrolü

---

## 1. Veritabanı Değişiklikleri

### `qa_pairs` tablosu
```sql
ALTER TABLE qa_pairs ADD COLUMN is_campaign BOOLEAN DEFAULT FALSE;
```

### `kb_chunks` tablosu
```sql
ALTER TABLE kb_chunks ADD COLUMN approved BOOLEAN DEFAULT FALSE;
UPDATE kb_chunks SET approved = FALSE;  -- Mevcut 72 chunk pending'e düşer
```

### Deluge script
`search-kb` Edge Function çağrısına `approved=eq.true` filtresi eklenir. Bot sadece onaylı chunk'ları görür.

---

## 2. Pipeline Değişiklikleri

### `1_fetch_transcripts.py` — Affiliate Tespiti

Konuşma kaydedilirken mesaj metinleri taranır. Aşağıdaki keyword'lerden herhangi biri geçiyorsa tüm konuşmanın `qa_pairs`'i `is_campaign = TRUE` olarak işaretlenir:

```python
CAMPAIGN_KEYWORDS = [
    "ruby vegas", "ruby casino", "rubyvegas", "rubycasino",
    "romus casino", "romuscasino",
    "captain slots", "captainslots",
    "affiliate", "lien d'inscription", "lien ruby",
]
```

### `5_update_kb.py` — Filtreler

1. `LOOKBACK_DAYS = 90` (30 → 90 gün)
2. `qa_pairs` çekerken `is_campaign=eq.false` filtresi eklenir
3. Üretilen chunk'lar `approved = FALSE` olarak kaydedilir (mevcut `upsert_chunk` fonksiyonu güncellenir)

---

## 3. Approval Web UI

**Stack:** Next.js (App Router) + Supabase JS client  
**Host:** Vercel  
**Auth:** Tek admin şifresi (`ADMIN_PASSWORD` env var), session cookie

### Sayfalar

**`/login`**  
Şifre formu. Başarılıysa cookie set edilir. Tüm diğer route'lar middleware ile korunur.

**`/` — Chunk Listesi**  
- Pending / Approved / Rejected tab filtresi
- Her chunk kartı: brand etiketi, kategori, başlık, içerik (expandable)
- Aksiyonlar: ✅ Onayla / ❌ Reddet / ✏️ Düzenle (inline edit)

**`/new` — Yeni Chunk Ekle**  
Form alanları:
- Brand: `romus` / `captain` (dropdown)
- Kategori: mevcut 36 kategori (dropdown)
- Başlık (text input)
- İçerik (textarea, markdown)

Kaydet → Supabase'e `approved = FALSE` olarak girer → listede Pending görünür → onaylanınca bot kullanır.

### Ortam Değişkenleri (Vercel)
```
ADMIN_PASSWORD=...
NEXT_PUBLIC_SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
```

---

## Akış Özeti

```
Zoho transcript gelir
    ↓
1_fetch_transcripts.py
    → affiliate keyword var mı? → is_campaign = TRUE/FALSE
    → Supabase qa_pairs'e yaz
    ↓
5_update_kb.py (günde 2x, GitHub Actions)
    → Son 90 günün is_campaign=FALSE qa_pairs'ini çek
    → Claude ile chunk üret
    → kb_chunks'a approved=FALSE olarak kaydet
    ↓
Approval UI (Vercel)
    → Admin chunk'ı inceler
    → Onayla → approved=TRUE → bot kullanır
    → Reddet → approved=FALSE kalır
    → Manuel chunk ekle → approved=FALSE → onay bekler
    ↓
Deluge script
    → Sadece approved=TRUE chunk'ları çeker
```

---

## Kapsam Dışı

- Otomatik onay mekanizması (güven skoru, vb.)
- Email/Slack bildirimi (yeni pending chunk var)
- Chunk versiyon geçmişi
