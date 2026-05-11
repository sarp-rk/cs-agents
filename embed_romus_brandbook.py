"""Generate embeddings for romus brandbook chunks that have no embedding yet."""
import os, requests
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json",
}

def generate_embedding(text):
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={"model": "text-embedding-3-small", "input": text},
    )
    return r.json()["data"][0]["embedding"]

# Get romus brandbook chunks
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/kb_chunks?brand=eq.romus&category=like.brandbook_*&select=id,category,title,content",
    headers=HEADERS,
)
chunks = resp.json()
print(f"{len(chunks)} brandbook chunk bulundu")

for chunk in chunks:
    print(f"Embedding: {chunk['category']}...", end=" ")
    embedding = generate_embedding(chunk["title"] + "\n" + chunk["content"])
    patch = requests.patch(
        f"{SUPABASE_URL}/rest/v1/kb_chunks?id=eq.{chunk['id']}",
        headers={**HEADERS, "Prefer": "return=minimal"},
        json={"embedding": embedding},
    )
    if patch.status_code in (200, 204):
        print("OK")
    else:
        print(f"FAIL {patch.status_code} {patch.text}")

print("Tamamlandı!")
