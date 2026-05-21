import json, os, sys, requests
from collections import defaultdict
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

URL = os.getenv('SUPABASE_URL')
KEY = os.getenv('SUPABASE_SERVICE_KEY')
H = {'Authorization': f'Bearer {KEY}', 'apikey': KEY}

# Fetch all rows with pagination
all_rows = []
offset = 0
while True:
    resp = requests.get(
        f'{URL}/rest/v1/qa_pairs',
        params={
            'conv_date': 'gte.2026-04-01',
            'select': 'conv_id,question,conv_date',
            'order': 'conv_date.asc,conv_id.asc',
            'limit': 1000,
            'offset': offset,
        },
        headers=H
    ).json()
    if not resp:
        break
    all_rows.extend(resp)
    if len(resp) < 1000:
        break
    offset += 1000

print(f"Total rows fetched: {len(all_rows)}", file=sys.stderr)

# Group by conv_id, keep first 3 questions per conv
convs = defaultdict(list)
for row in all_rows:
    convs[row['conv_id']].append(row)

print(f"Unique conversations: {len(convs)}", file=sys.stderr)

# Build compact text — first 3 questions per conv
conv_text = ''
for i, (cid, msgs) in enumerate(convs.items()):
    date = msgs[0].get('conv_date', '')[:10]
    conv_text += f'\n[K{i+1}] {date}\n'
    for m in msgs[:3]:
        q = (m.get('question') or '').strip()[:200]
        if q:
            conv_text += f'  - {q}\n'

client = Anthropic()
resp = client.messages.create(
    model='claude-opus-4-7',
    max_tokens=4000,
    messages=[{
        'role': 'user',
        'content': f'''Aşağıda Nisan 2026 başından itibaren {len(convs)} müşteri konuşması var.
Her konuşmada ilk 3 müşteri sorusu var.

Şunları analiz et:

1. **Konu Dağılımı** — En sık gelen konular, kaç konuşmada geçtiği ve yüzdesi
2. **Bot Yapabilir mi?** — Konular için: EVET / KISMI / HAYIR kategorizasyonu
3. **Dikkat Çeken Trendler** — Öne çıkan sorunlar, tekrar eden şikayetler
4. **Özet** — 3-5 cümle genel değerlendirme

Türkçe yaz. Sayısal veriler olsun. Kısa ve net.

KONUŞMALAR:
{conv_text}'''
    }]
)
print(resp.content[0].text)
