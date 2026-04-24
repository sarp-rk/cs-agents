"""
6_translate_chunks.py — Translate French kb_chunks to English

Supabase'deki kb_chunks tablosundaki Fransızca içerikleri Claude Haiku ile
İngilizceye çevirir ve yerinde günceller.
"""
import os
import sys
import time
import requests
import anthropic
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SB_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=minimal",
}

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a professional translator specializing in casino customer support content.
Translate the given French casino customer support knowledge base content to English.

Rules:
- Translate accurately and naturally
- Keep casino/gambling terminology correct (e.g., "wagering", "free spins", "cashout")
- Keep placeholders like {brand}, {amount} unchanged
- Keep the same tone (professional, helpful)
- Output ONLY the translated text, nothing else"""


def is_french(text: str) -> bool:
    """Heuristic check for French content."""
    if not text:
        return False
    french_indicators = [
        "vous ", "votre ", "notre ", "nous ", "est ", "les ", "des ",
        "pour ", "avec ", "dans ", "sur ", "dépôt", "retrait", "bonus",
        "jeux", "compte", "contactez", "wagering", "mise",
    ]
    text_lower = text.lower()
    hits = sum(1 for word in french_indicators if word in text_lower)
    return hits >= 3


def translate_text(text: str) -> str:
    """Translate French text to English using Claude Haiku."""
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text.strip()


def fetch_all_chunks() -> list[dict]:
    """Fetch only pending (approved=false) kb_chunks from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/kb_chunks"
    params = {"select": "id,brand,category,title,content", "approved": "eq.false"}
    resp = requests.get(url, headers=SB_HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def update_chunk(chunk_id: int, new_content: str, new_title: str):
    """Update a single chunk's content and title in Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/kb_chunks"
    params = {"id": f"eq.{chunk_id}"}
    payload = {"content": new_content, "title": new_title}
    resp = requests.patch(url, headers=SB_HEADERS, params=params, json=payload)
    resp.raise_for_status()


def main():
    print("Fetching all kb_chunks...")
    chunks = fetch_all_chunks()
    print(f"Total chunks: {len(chunks)}")

    # Tüm chunk'ları çevir (is_french heuristic'i bazılarını kaçırıyordu)
    french_chunks = chunks
    print(f"Chunks to translate: {len(french_chunks)}")

    if not french_chunks:
        print("No French chunks found. Exiting.")
        return

    translated = 0
    failed = 0

    for i, chunk in enumerate(french_chunks, 1):
        chunk_id = chunk["id"]
        brand = chunk.get("brand", "?")
        category = chunk.get("category", "?")
        title = chunk.get("title", "?")
        content = chunk.get("content", "")

        print(f"\n[{i}/{len(french_chunks)}] {brand}/{category} — {title} (id={chunk_id})")
        print(f"  Preview: {content[:80].replace(chr(10), ' ')}...")

        try:
            translated_title = translate_text(title)
            translated_text = translate_text(content)
            update_chunk(chunk_id, translated_text, translated_title)
            print(f"  ✓ Translated title: {translated_title}")
            translated += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

        # Rate limiting — Haiku is fast but let's be polite
        if i < len(french_chunks):
            time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Done! Translated: {translated}, Failed: {failed}")


if __name__ == "__main__":
    main()
