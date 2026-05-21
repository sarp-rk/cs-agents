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
            'select': 'conv_id,question,answer,conv_date',
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

print(f"Total rows: {len(all_rows)}", file=sys.stderr)

# Group by conv_id
convs = defaultdict(list)
for row in all_rows:
    convs[row['conv_id']].append(row)

# Group conv_ids by date
by_date = defaultdict(list)
for cid, msgs in convs.items():
    date = (msgs[0].get('conv_date') or '')[:10]
    by_date[date].append((cid, msgs))

print(f"Unique conversations: {len(convs)}, Days: {len(by_date)}", file=sys.stderr)

# Build compact text per day
conv_text = ''
for date in sorted(by_date.keys()):
    day_convs = by_date[date]
    conv_text += f'\n### {date} ({len(day_convs)} conversations)\n'
    for cid, msgs in day_convs:
        questions = [m.get('question','').strip()[:150] for m in msgs[:2] if m.get('question','').strip()]
        if questions:
            conv_text += f'  - {" | ".join(questions)}\n'

client = Anthropic()
resp = client.messages.create(
    model='claude-opus-4-7',
    max_tokens=8000,
    messages=[{
        'role': 'user',
        'content': f'''You are analyzing {len(convs)} customer service chat conversations from April 1, 2026 to present, for two online casino brands (RomusCasino and CaptainSlots). Customers speak French.

Below is a day-by-day breakdown of conversations with the first 1-2 customer messages per conversation.

Write a detailed English report with these sections:

## 1. Daily Volume Table
A markdown table: | Date | Chats | Top Topics That Day |
Include every day that has data.

## 2. Topic Breakdown (Overall)
Full breakdown with counts and percentages. Be specific — split bonus into subcategories (deposit bonus request, no-deposit/free spins, birthday bonus, VIP cashback, etc.)

## 3. Week-by-Week Trend
What changed week by week? Volume trends, topic shifts.

## 4. Critical Issues
Specific recurring problems that need urgent attention. Quote actual customer messages where impactful.

## 5. Bot Automation Potential
For each major topic category: can bot handle it (YES/PARTIAL/NO) and why.

## 6. Executive Summary
5-7 sentences. Key numbers, biggest risks, top recommendation.

Be precise with numbers. Use the day-by-day data to calculate daily counts accurately.

DATA:
{conv_text}'''
    }]
)
print(resp.content[0].text)
