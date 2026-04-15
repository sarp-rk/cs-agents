"""
6_scrape_promotions.py — Promotions page -> KB chunks (Supabase)

Casino promotions sayfasını çeker, Claude ile yapılandırır,
ilgili KB chunk'larını günceller.
"""
import os
import sys
import requests
import anthropic
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SB_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
}

client = anthropic.Anthropic()

PROMO_PAGES = {
    "romus":   "https://romuscasino1.com/en/promotions",
    "captain": "https://captainslots.com/en/promotions",
}

# Which KB categories to update from the promotions page
PROMO_CATEGORIES = [
    "bonus_welcome_pack",
    "bonus_happy_hour",
    "bonus_weekly_promos",
    "bonus_nodep_freespins",
]


def fetch_page_text(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        # Strip HTML tags roughly
        text = r.text
        import re
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:8000]  # limit to avoid token overflow
    except Exception as e:
        print(f"  Page fetch error: {e}")
        return None


def generate_embedding(text):
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "text-embedding-3-small", "input": text},
    )
    return r.json()["data"][0]["embedding"]


def get_existing_chunk(brand, category):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/kb_chunks",
        headers={**SB_HEADERS, "Prefer": ""},
        params={"brand": f"eq.{brand}", "category": f"eq.{category}", "select": "id,title,content"},
    )
    rows = r.json()
    return rows[0] if rows else None


def update_chunk(chunk_id, title, content):
    embedding = generate_embedding(title + "\n" + content)
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/kb_chunks?id=eq.{chunk_id}",
        headers=SB_HEADERS,
        json={
            "title":      title,
            "content":    content,
            "embedding":  embedding,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def rebuild_chunk_from_page(brand, category, page_text, existing_content):
    existing_section = f"\n\nExisting KB content (keep what's still accurate, update what changed):\n{existing_content}" if existing_content else ""

    prompt = f"""You are maintaining a casino customer support knowledge base for {brand.title()} Casino.
Category: {category}

Below is the raw text scraped from the casino's promotions page:
{page_text}
{existing_section}

Extract and write a knowledge base section IN FRENCH covering only the {category.replace('_', ' ')} topic.
Rules:
- Only use information explicitly present on the page or in existing content
- Include: amounts, percentages, free spin counts, eligible games, timing, expiry (if mentioned)
- General expiry rule if not specified: free spins/bonuses expire after 7 days if not claimed
- Markdown format: ## title, bullet points
- Max 2000 characters
- Be specific with numbers and conditions

Return ONLY the markdown content."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def main():
    for brand, url in PROMO_PAGES.items():
        print(f"── {brand.title()} ({url}) ──")
        page_text = fetch_page_text(url)
        if not page_text:
            print(f"  Sayfa alınamadı, atlanıyor.")
            continue
        print(f"  {len(page_text)} karakter çekildi")

        for category in PROMO_CATEGORIES:
            existing = get_existing_chunk(brand, category)
            if not existing:
                print(f"  ✗ {category}: chunk bulunamadı")
                continue

            try:
                content = rebuild_chunk_from_page(brand, category, page_text, existing["content"])
                lines = content.strip().splitlines()
                title = lines[0].lstrip("#").strip() if lines else f"{brand} {category}"
                update_chunk(existing["id"], title, content)
                print(f"  ✓ {category} ({len(content)} karakter)")
            except Exception as e:
                print(f"  ✗ {category}: {e}")

        print()

    print("Tamamlandı!")


if __name__ == "__main__":
    main()
