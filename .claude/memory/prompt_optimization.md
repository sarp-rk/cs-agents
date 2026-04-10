# Prompt Optimization — Token Reduction

## Karar (2026-04-03)
Supabase Console'da input token ~2500/mesaj görüldü. Ana neden: base prompt ~629 token.

## Dosyalar
- `data/system_prompt_v1_backup.txt` — orijinal (~629 token)
- `data/system_prompt_v2.txt` — optimize (~220 token, %65 daha az)

## v2'de Neler Değişti
- Verbose açıklamalar kaldırıldı ("Act like a real human agent — not a chatbot" gibi)
- "What you CAN do" bölümü kaldırıldı
- "Your Role" bullet listesi kaldırıldı
- Rules kısmı **korundu** — KB'e güvenmek riskli, yanlış chunk gelirse bot bilmez
- HANDOFF trigger listesi **korundu** — kritik

## Test Süreci
1. `deluge_final.js`'i v2 prompt ile güncelle
2. Zobot'a yapıştır, aynı soruları sor
3. Anthropic Console → Usage'dan token farkını gözlemle
4. HANDOFF doğru tetikleniyor mu kontrol et
5. Sorun varsa `system_prompt_v1_backup.txt`'e dön
