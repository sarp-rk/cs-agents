"""Insert Romus brandbook chunks into Supabase kb_chunks table."""
import os, json, requests
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
HEADERS = {
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

chunks = [
    {
        "brand": "romus",
        "category": "brandbook_general",
        "title": "General Info - Romus Casino",
        "content": """## General Info - Romus Casino

- Established: 2026
- Games: 4000+
- Languages: English, French, French Canadian
- Currencies: EUR, CAD
- Min deposit: 20 €/$ (CAD: $30)
- Website: romuscasino1.com
""",
        "approved": True,
    },
    {
        "brand": "romus",
        "category": "brandbook_welcome_bonus",
        "title": "Welcome Bonus - Romus Casino",
        "content": """## Welcome Bonus - Romus Casino

### FR/BE/LU/RE/CH/CA
3000 EUR + 150 FS Welcome Package

- 1st Welcome Bonus: 100% up to 1000€ OR 200 FS on Le Bandit
- 2nd Welcome Bonus: 100% up to 1000€ + 50 FS on Le Bandit
- 3rd Welcome Bonus: 100% up to 1000€ + 100 FS on Legion Gold

### Sweden (SE)
3000 EUR + 500 FS Welcome Package

- 1st Welcome Bonus: 150% up to 1000€ + 100 FS on Book of Dead
- 2nd Welcome Bonus: 100% up to 1000€ + 150 FS on Le Viking
- 3rd Welcome Bonus: 50% up to 1000€ + 250 FS on Thunder Coins XXL: Hold and Win

### Wagering
- Deposit bonus: 40x (NON - STICKY) — on the welcome bonus package
- Free spins: 40x
- Max cashout: 10x deposit
""",
        "approved": True,
    },
    {
        "brand": "romus",
        "category": "brandbook_weekly_promos",
        "title": "Weekly Promotions - Romus Casino",
        "content": """## Weekly Promotions - Romus Casino

- **Tuesday — Lupa's Tuesday**: Free spins with deposit, different game every week (wagering: 1x)
- **Friday — The Senate's Friday**: Free spins with deposit on different games every week (wagering: 1x)
- **Weekend — Weekend's Legion**: Different % bonus offers every week (wagering: 40x)
- **Mystery Day — Happy Hour**: From 4:30pm till 11:59pm — unlimited free spins (wagering: 1x)
""",
        "approved": True,
    },
    {
        "brand": "romus",
        "category": "brandbook_limits",
        "title": "Deposit & Withdrawal Limits - Romus Casino",
        "content": """## Deposit & Withdrawal Limits - Romus Casino

### Deposit
- Minimum: 20 €/$ (CAD: $30)
- Maximum per transaction: 5000 EUR/CAD

### Withdrawal
- Minimum: 30 €/$
- Bonus max cashout: 10x the deposit amount (e.g. 20€ deposit → max 200€ withdrawal)

### Bonus Rules
- Max bet with active bonus: 5€/spin
- Bonus cannot be used on: live casino, jackpot slots, table games
""",
        "approved": True,
    },
    {
        "brand": "romus",
        "category": "brandbook_payment_methods",
        "title": "Payment Methods - Romus Casino",
        "content": """## Payment Methods - Romus Casino

### Deposit Options (FR/BE/LU/RE/CH/CA)
Visa, MasterCard, Apple Pay, Google Pay, Instant Banking, Revolut, PaysafeCard

### Withdrawal
Bank Transfer

### Canada
- Deposit: Credit Card
- Withdrawal: Bank Transfer
""",
        "approved": True,
    },
    {
        "brand": "romus",
        "category": "brandbook_contact",
        "title": "Contact & Support - Romus Casino",
        "content": """## Contact & Support - Romus Casino

- Email: support@romuscasino.com
- Live Chat: Yes
- Phone: Available to selected VIPs
- Website: romuscasino1.com
""",
        "approved": True,
    },
]

for chunk in chunks:
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/kb_chunks",
        headers=HEADERS,
        json=chunk,
    )
    if resp.status_code in (200, 201):
        print(f"OK: {chunk['category']}")
    else:
        print(f"FAIL: {chunk['category']} — {resp.status_code} {resp.text}")
