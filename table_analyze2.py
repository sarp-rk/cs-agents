import json, os, sys, requests
from collections import defaultdict
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

URL = os.getenv('SUPABASE_URL')
KEY = os.getenv('SUPABASE_SERVICE_KEY')
H = {'Authorization': f'Bearer {KEY}', 'apikey': KEY}

qa = requests.get(
    f'{URL}/rest/v1/qa_pairs?conv_date=gte.2026-04-26&select=conv_id,question,answer,conv_date&order=conv_date.asc&limit=500',
    headers=H
).json()

convs = defaultdict(list)
for row in qa:
    convs[row['conv_id']].append(row)

conv_list = list(convs.items())

# Second batch: K105-K188
conv_text = ''
for i, (cid, msgs) in enumerate(conv_list[104:], start=105):
    conv_text += f'\n[K{i}]\n'
    for m in msgs[:6]:
        conv_text += f'M: {m["question"][:250]}\nA: {m["answer"][:250]}\n'

client = Anthropic()
resp = client.messages.create(
    model='claude-sonnet-4-6',
    max_tokens=6000,
    messages=[{
        'role': 'user',
        'content': f'''Aşağıda müşteri konuşmaları var [K105]-[K188] şeklinde etiketlenmiş.

Her konuşmayı analiz edip aşağıdaki formatta Markdown tablosu oluştur. Sadece tablo satırları yaz, başlık satırı yazma.

Sütunlar (bu sırayla):
Konuşma | Kategori | Alt Kategori | Müşterinin İsteği (özet) | Çözüldü mü? | Çözüm Yöntemi | Bot Yapabilir mi? | Neden / Ne Gerekir?

Kategori değerleri:
BONUS_TALEP / BONUS_SORUN / WITHDRAWAL_BEKLEYEN / WITHDRAWAL_LIMIT / WITHDRAWAL_KAYIP / CASHBACK / VIP / KYC / TEKNIK / HESAP / BILGI_SORUSU

Bot Yapabilir mi: EVET / KISMI / HAYIR

KONUŞMALAR:
{conv_text}'''
    }]
)
print(resp.content[0].text)
