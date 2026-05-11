import os, requests
from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
HEADERS = {"Authorization": f"Bearer {SUPABASE_KEY}", "apikey": SUPABASE_KEY, "Content-Type": "application/json", "Prefer": "return=minimal"}

content = """## How to Make a Deposit at Romus Casino

### Steps
1. Log in to your account
2. Click on the Deposit button
3. Select your preferred payment method
4. Enter the amount (minimum 20€, or $30 CAD)
5. Follow the instructions to complete the payment

### Available Payment Methods

**FR/BE/LU/RE/CH/CA:**
Visa, MasterCard, Apple Pay, Google Pay, Instant Banking, Revolut, PaysafeCard

**Canada:**
Credit Card

### Withdrawal Methods
Bank Transfer

### Limits
- Minimum deposit: 20€ (CAD: $30)
- Maximum per transaction: 5000 EUR/CAD
"""

# generate new embedding
emb = requests.post("https://api.openai.com/v1/embeddings",
    headers={"Authorization": f"Bearer {OPENAI_KEY}"},
    json={"model": "text-embedding-3-small", "input": "Deposit Guide - Romus Casino\n" + content}
).json()["data"][0]["embedding"]

r = requests.patch(
    f"{SUPABASE_URL}/rest/v1/kb_chunks?brand=eq.romus&category=eq.deposit_process",
    headers=HEADERS,
    json={"content": content, "embedding": emb}
)
print(r.status_code, r.text[:200] if r.text else "OK")
