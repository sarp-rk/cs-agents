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

conv_text = ''
for i, (cid, msgs) in enumerate(list(convs.items())):
    conv_text += f'\n[K{i+1}]\n'
    for m in msgs[:6]:
        conv_text += f'M: {m["question"][:250]}\nA: {m["answer"][:250]}\n'

client = Anthropic()
resp = client.messages.create(
    model='claude-sonnet-4-6',
    max_tokens=8000,
    messages=[{
        'role': 'user',
        'content': f'''Aşağıda {len(convs)} müşteri konuşması var [K1], [K2]... şeklinde etiketlenmiş.

Her konuşmayı analiz edip aşağıdaki formatta bir Markdown tablosu oluştur.

Tablo sütunları:
| Konuşma | Kategori | Alt Kategori | Müşterinin İsteği (özet) | Çözüldü mü? | Çözüm Yöntemi | Bot Yapabilir mi? | Neden / Ne Gerekir? |

Kategori değerleri (bunları kullan):
- BONUS_TALEP
- BONUS_SORUN
- WITHDRAWAL_BEKLEYEN
- WITHDRAWAL_LIMIT
- WITHDRAWAL_KAYIP
- CASHBACK
- VIP
- KYC
- TEKNIK
- HESAP
- BILGI_SORUSU

Bot Yapabilir mi sütunu için:
- EVET — genel bilgi, kural açıklama
- KISMI — bazı bilgiyi verebilir ama aksiyon için agent lazım
- HAYIR — hesap aksiyonu, backoffice, discretionary karar

Tüm {len(convs)} konuşmayı tek tabloya yaz. Özlü ol, her satır max 2 satır metin.

KONUŞMALAR:
{conv_text}'''
    }]
)
print(resp.content[0].text)
