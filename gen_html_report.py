import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import markdown
from dotenv import load_dotenv
load_dotenv()

with open('analyze_report.md', encoding='utf-8') as f:
    md_content = f.read()

html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CS Chat Analysis — RomusCasino & CaptainSlots</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f7fa;
    color: #1a1a2e;
    line-height: 1.7;
  }}
  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
    padding: 48px 40px;
    text-align: center;
  }}
  .header h1 {{
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 8px;
  }}
  .header p {{
    opacity: 0.75;
    font-size: 1rem;
  }}
  .stats-bar {{
    display: flex;
    justify-content: center;
    gap: 40px;
    background: #0f3460;
    padding: 20px 40px;
    flex-wrap: wrap;
  }}
  .stat {{
    text-align: center;
    color: white;
  }}
  .stat .number {{
    font-size: 2rem;
    font-weight: 800;
    color: #e94560;
  }}
  .stat .label {{
    font-size: 0.75rem;
    opacity: 0.75;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .container {{
    max-width: 1100px;
    margin: 40px auto;
    padding: 0 24px;
  }}
  .section {{
    background: white;
    border-radius: 12px;
    padding: 36px 40px;
    margin-bottom: 28px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }}
  h2 {{
    font-size: 1.4rem;
    color: #0f3460;
    border-bottom: 3px solid #e94560;
    padding-bottom: 10px;
    margin-bottom: 24px;
  }}
  h3 {{
    font-size: 1.1rem;
    color: #1a1a2e;
    margin: 24px 0 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  h4 {{
    font-size: 0.95rem;
    color: #0f3460;
    margin: 20px 0 8px;
  }}
  p {{ margin-bottom: 12px; color: #444; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
    margin: 16px 0;
  }}
  th {{
    background: #0f3460;
    color: white;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
  }}
  td {{
    padding: 9px 14px;
    border-bottom: 1px solid #eef0f4;
    vertical-align: top;
  }}
  tr:nth-child(even) td {{ background: #f8f9fc; }}
  tr:last-child td {{ font-weight: 700; background: #e8edf5; }}
  blockquote {{
    border-left: 4px solid #e94560;
    background: #fff5f7;
    margin: 12px 0;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    font-style: italic;
    color: #555;
    font-size: 0.9rem;
  }}
  ul, ol {{
    padding-left: 20px;
    margin: 8px 0 12px;
    color: #444;
  }}
  li {{ margin-bottom: 4px; }}
  strong {{ color: #1a1a2e; }}
  code {{
    background: #f0f2f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.85em;
    color: #e94560;
  }}
  .priority-immediate {{ border-left: 5px solid #e94560; }}
  .priority-short {{ border-left: 5px solid #f0a500; }}
  .priority-long {{ border-left: 5px solid #2ecc71; }}
  .badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-left: 8px;
  }}
  .badge-red {{ background: #fde8ec; color: #e94560; }}
  .badge-yellow {{ background: #fef6e4; color: #d4890a; }}
  .badge-green {{ background: #e8f8f0; color: #1e8449; }}
  hr {{ border: none; border-top: 1px solid #eef0f4; margin: 24px 0; }}
  .footer {{
    text-align: center;
    color: #999;
    font-size: 0.8rem;
    padding: 32px;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>Customer Service Chat Analysis</h1>
  <p>RomusCasino &amp; CaptainSlots &nbsp;|&nbsp; April 28 – May 19, 2026</p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="number">1,122</div><div class="label">Total Conversations</div></div>
  <div class="stat"><div class="number">99</div><div class="label">Peak Day (May 7)</div></div>
  <div class="stat"><div class="number">52%</div><div class="label">Bonus Requests</div></div>
  <div class="stat"><div class="number">17%</div><div class="label">Withdrawal Issues</div></div>
  <div class="stat"><div class="number">~60%</div><div class="label">Automation Potential</div></div>
</div>

<div class="container">
{html_body}
</div>

<div class="footer">
  Generated {__import__('datetime').date.today().strftime('%B %d, %Y')} &nbsp;|&nbsp; CS Agents Analytics
</div>

</body>
</html>"""

with open('cs_analysis_report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved: cs_analysis_report.html")
