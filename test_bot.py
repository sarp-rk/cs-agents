import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
import anthropic

load_dotenv()

SYSTEM_PROMPT = Path("data/system_prompt.txt").read_text(encoding="utf-8")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

TEST_MESSAGES = [
    ("Selamlama", "Bonjour"),
    ("Bonus gelmedi", "J'ai fait un dépôt de 50€ mais je n'ai pas reçu mon bonus"),
    ("Withdrawal süresi", "Combien de temps pour que mon retrait soit traité ?"),
    ("Hesap kapatma", "Je veux fermer mon compte définitivement"),
    ("Bloke retrait", "Pourquoi mon retrait est bloqué depuis 5 jours ? Je veux parler à quelqu'un"),
    ("Max cashout sorusu", "J'ai déposé 20€ et j'ai gagné 500€ avec le bonus, combien je peux retirer ?"),
]


def ask(message):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message}],
    )
    return response.content[0].text


def translate_to_turkish(text):
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": f"Türkçeye çevir (kısa ve doğal):\n{text}"}],
    )
    return response.content[0].text


print("=" * 60)
print("CS BOT TEST")
print("=" * 60)

for label, msg in TEST_MESSAGES:
    print(f"\n{'=' * 60}")
    print(f"[{label}]")
    msg_tr = translate_to_turkish(msg)
    print(f"Müşteri : {msg_tr}")
    reply = ask(msg)
    reply_tr = translate_to_turkish(reply)
    print(f"Bot     : {reply_tr}")
    handoff = any(p in reply for p in ["transférer", "transfer to an agent"])
    if handoff:
        print("\n>>> AGENT'A DEVİR TETİKLENİR <<<")
    time.sleep(5)
