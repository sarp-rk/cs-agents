import json, os, sys
from collections import defaultdict
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('qa_recent.json', encoding='utf-8'))

convs = defaultdict(list)
for row in data:
    convs[row['conv_id']].append(row)

print(f"Toplam konuşma: {len(convs)}, qa_pair: {len(data)}")

conv_text = ''
for i, (cid, msgs) in enumerate(list(convs.items())[:80]):
    conv_text += f'--- Konuşma {i+1} ({msgs[0].get("conv_date","")[:10]}) ---\n'
    for m in msgs[:6]:
        conv_text += f'Müşteri: {m["question"][:200]}\n'
        conv_text += f'Agent: {m["answer"][:200]}\n'
    conv_text += '\n'

client = Anthropic()
resp = client.messages.create(
    model='claude-sonnet-4-6',
    max_tokens=4000,
    messages=[{
        'role': 'user',
        'content': f'''Asagida son 15 gunden {len(convs)} musteri konusmasi var. Bunlari analiz et ve su soruları yanıtla:

1. En sik sorulan konular/kategoriler neler? (frekansla birlikte)
2. Hangi sorunlar agent tarafindan cozuldu? Nasil cozuldu?
3. Hangi sorunlar icin musteri account datasi gerekti? (bakiye, bonus durumu, KYC, withdrawal history vb)
4. Hangi islemler backoffice/sistem erisimi gerektirdi? (bonus kredileme, withdrawal onaylama, account acma vb)
5. Bot hangi konulari cevaplayabilir, hangilerini kesinlikle agente devretmeli?
6. Bot daha iyi yapilabilmesi icin hangi KB kategorileri eksik veya zayif?

Turkce ve ozlu yaz. Madde madde.

KONUSMALAR:
{conv_text}'''
    }]
)
print(resp.content[0].text)
