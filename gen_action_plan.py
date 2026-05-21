import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

with open('analyze_report.md', encoding='utf-8') as f:
    report = f.read()

client = Anthropic()
resp = client.messages.create(
    model='claude-opus-4-7',
    max_tokens=4000,
    messages=[{
        'role': 'user',
        'content': f'''Based on this customer service analysis report, write a detailed Action Plan section in English.

Format:
## 7. Action Plan

Group by priority: IMMEDIATE (this week), SHORT-TERM (this month), LONG-TERM (next quarter).

For each action item include:
- **What**: specific action
- **Why**: which critical issue it solves (reference section 4 where relevant)
- **Owner**: who should do it (CS team / Tech team / Compliance / Management)
- **Metric**: how to measure success

Be concrete and operational. No vague recommendations.

REPORT:
{report}'''
    }]
)

action_plan = resp.content[0].text

# Append to report
with open('analyze_report.md', 'a', encoding='utf-8') as f:
    f.write('\n\n---\n\n')
    f.write(action_plan)

print("Done. Action plan appended to analyze_report.md")
