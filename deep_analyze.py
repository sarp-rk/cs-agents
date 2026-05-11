import json, os, sys, requests
from collections import defaultdict
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

URL = os.getenv('SUPABASE_URL')
KEY = os.getenv('SUPABASE_SERVICE_KEY')
H = {'Authorization': f'Bearer {KEY}', 'apikey': KEY}

# Fetch all qa_pairs last 15 days
qa = requests.get(
    f'{URL}/rest/v1/qa_pairs?conv_date=gte.2026-04-26&select=conv_id,question,answer,conv_date&order=conv_date.desc&limit=500',
    headers=H
).json()

# Fetch relevant KB chunks
kb_cats = [
    'vip_cashback','vip_how_to_join','vip_levels',
    'withdrawal_limits','withdrawal_pending','withdrawal_process',
    'bonus_wagering','bonus_max_cashout','bonus_activation',
    'bonus_cancellation_rules','bonus_eligible_games','bonus_loss_request',
    'bonus_welcome_pack','bonus_weekly_promos',
    'brandbook_limits','brandbook_welcome_bonus'
]
kb_filter = ','.join(kb_cats)
kb_chunks = requests.get(
    f'{URL}/rest/v1/kb_chunks?brand=eq.romus&category=in.({kb_filter})&select=category,title,content&approved=eq.true',
    headers=H
).json()

kb_text = ''
for chunk in kb_chunks:
    kb_text += f'\n=== KB: {chunk["category"]} ===\n{chunk["title"]}\n{chunk["content"][:600]}\n'

# Group conversations
convs = defaultdict(list)
for row in qa:
    convs[row['conv_id']].append(row)

# Build full conversation text - all 188
conv_text = ''
for i, (cid, msgs) in enumerate(list(convs.items())):
    conv_text += f'\n--- Konuşma {i+1} ({msgs[0].get("conv_date","")[:10]}) ---\n'
    for m in msgs[:8]:
        conv_text += f'MÜŞTERİ: {m["question"][:300]}\n'
        conv_text += f'AGENT: {m["answer"][:300]}\n'

client = Anthropic()
resp = client.messages.create(
    model='claude-sonnet-4-6',
    max_tokens=6000,
    messages=[{
        'role': 'user',
        'content': f'''Aşağıda iki şey var:
1. Mevcut KB chunk içerikleri (botun bildiği şeyler)
2. Son 15 günün gerçek müşteri-agent konuşmaları

Detaylı analiz yap:

**A. Manuel Bonus Talepleri — Ne Tür Bonuslar?**
- Tam olarak hangi bonus türleri isteniyor? (loyalty, no-dep, free spin, cashback, doğum günü vs.)
- Her türün nasıl işlendiğini yaz (agent ne kontrol etti, ne verdi, hangi kriterlere baktı)
- Bu bonusların hangisi kurala bağlı (sabit kriter var), hangisi discretionary (agent kararı)?
- Bot hangi sınırlar içinde otomatik verebilir? Hangi bilgiye/sisteme ihtiyaç var?

**B. Withdrawal Sorunları — Tam Akış**
- Müşteri ne soruyor tam olarak?
- Agent tam olarak ne yapıyor? (neyi kontrol ediyor, neyi iletiliyor, ne söylüyor)
- Çözüm için hangi bilgi/sistem erişimi gerekiyor?
- Bot withdrawal konusunda ne söyleyebilir, ne söyleyemez?

**C. Mevcut KB vs Gerçek Sorular — Gap Analizi**
KB içerikleri verildi. Her kategori için:
- KB'de ne yazıyor (özet)
- Müşteriler bu konuda gerçekte ne soruyor
- KB'nin hangi bilgisi eksik veya yanlış
- Ne eklenmeli (spesifik, somut)

Somut yaz. "Yetersiz" deme, tam olarak neyin eksik olduğunu yaz.

---
MEVCUT KB İÇERİKLERİ:
{kb_text}

---
GERÇEK KONUŞMALAR ({len(convs)} konuşma, {len(qa)} mesaj):
{conv_text}
'''
    }]
)
print(resp.content[0].text)
