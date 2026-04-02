"""
system_prompt.txt'i Deluge string formatına çevirip
deluge_script.js şablonundan deluge_final.js üretir.

Kullanım: py 4_generate_deluge.py
Çıktı:    deluge_final.js  → Zoho Zobot Code Block'a yapıştır
"""
from pathlib import Path

TEMPLATE = Path("deluge_script.js")
PROMPT_FILE = Path("data/system_prompt.txt")
OUTPUT = Path("deluge_final.js")


def escape_for_deluge(text: str) -> str:
    """Escape for Deluge string literal (double-quoted, single line).
    Strips non-Latin Unicode (emoji, special symbols) that break Deluge's parser.
    Keeps standard Latin + Latin Extended (U+0000–U+02FF) and common punctuation.
    """
    # Replace known problematic symbols before stripping
    replacements = {
        "➯": "-",
        "→": "->",
        "←": "<-",
        "↑": "^",
        "↓": "v",
        "⚓": "",
        "🙂": ":)",
        "😊": ":)",
        "👋": "",
        "✅": "OK",
        "❌": "NOK",
        "⭐": "*",
        "💬": "",
    }
    for ch, repl in replacements.items():
        text = text.replace(ch, repl)

    # Strip any remaining characters outside Latin Extended-B (U+0000–U+024F)
    text = "".join(c if ord(c) <= 0x024F else "" for c in text)

    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\r\n", "\\n")
    text = text.replace("\n", "\\n")
    return text


def main():
    template = TEMPLATE.read_text(encoding="utf-8")
    prompt_raw = PROMPT_FILE.read_text(encoding="utf-8")

    prompt_escaped = escape_for_deluge(prompt_raw)
    import os
    from dotenv import load_dotenv
    load_dotenv()

    result = template.replace('"<SYSTEM_PROMPT_BURAYA>"', f'"{prompt_escaped}"')
    result = result.replace('"<SUPABASE_URL_BURAYA>"', f'"{os.getenv("SUPABASE_URL", "")}"')
    result = result.replace('"<SUPABASE_ANON_KEY_BURAYA>"', f'"{os.getenv("SUPABASE_ANON_KEY", "")}"')

    if '"<SYSTEM_PROMPT_BURAYA>"' in template and '"<SYSTEM_PROMPT_BURAYA>"' not in result:
        print("Sistem promptu yerlestirildi.")
    else:
        print("HATA: Placeholder bulunamadi, deluge_script.js kontrol et.")
        return

    OUTPUT.write_text(result, encoding="utf-8")

    char_count = len(result)
    print(f"Dosya: {OUTPUT}")
    print(f"Boyut: {char_count:,} karakter ({char_count / 1024:.1f} KB)")

    if char_count > 500_000:
        print("UYARI: Zoho Deluge function limiti asılabilir (500KB).")
    else:
        print("Boyut OK — Deluge'a yapistirabilirsin.")

    print(f"\nSonraki adim:")
    print(f"  1. {OUTPUT} dosyasini ac")
    print(f"  2. <ANTHROPIC_API_KEY_BURAYA> satirini gercek API key ile degistir")
    print(f"  3. Zoho SalesIQ > Zobot > Code Block'a yapistir")


if __name__ == "__main__":
    main()
