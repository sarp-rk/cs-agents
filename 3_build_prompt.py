import json
import random
from pathlib import Path

KB_DIR = Path("data/knowledge_base")
QA_FILE = Path("data/qa_pairs.jsonl")
MANUAL_QA_FILE = Path("data/manual_qa.jsonl")
OUTPUT_FILE = Path("data/system_prompt.txt")

TOTAL_EXAMPLES = 50

# Kategori başına hedef örnek sayısı (transcript pool'dan)
CATEGORY_TARGETS = {
    "bonus":        10,
    "withdrawal":   10,
    "kyc":          8,
    "account":      6,
    "technical":    3,
    "vip":          2,
    "other":        1,
}

CATEGORY_KEYWORDS = {
    "bonus": [
        "bonus", "free spin", "freespin", "free spins", "tour gratuit", "tours gratuits",
        "wagering", "mise", "condition de mise", "cashout", "promotion", "offre",
    ],
    "withdrawal": [
        "retrait", "withdraw", "virement", "paiement", "payer", "versement",
        "remboursement", "encaissement", "pending", "en attente", "délai",
    ],
    "kyc": [
        "document", "pièce", "vérif", "kyc", "identité", "passeport", "rib",
        "carte bancaire", "justificatif", "preuve", "validation", "vérification",
        "compte vérifié", "attestation",
    ],
    "account": [
        "compte", "fermer", "bloquer", "mot de passe", "login", "inscription",
        "connexion", "email", "adresse", "modifier", "changer", "réouvrir",
        "réactiver", "fermeture", "clôture",
    ],
    "technical": [
        "jeu", "chargement", "bug", "connexion", "lag", "lent", "erreur",
        "problème technique", "ne fonctionne pas", "ne marche pas", "plante",
        "bloqué", "freeze",
    ],
    "vip": [
        "vip", "cashback", "manager", "fidélité", "niveau", "tier",
        "programme", "récompense",
    ],
}

TURKISH_INDICATORS = ["ş", "ğ", "ı", "ç", "ö", "ü", "Ş", "Ğ", "İ", "Ç", "Ö", "Ü"]


def is_turkish(text):
    return any(c in text for c in TURKISH_INDICATORS)


def categorize(question, answer):
    text = (question + " " + answer).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "other"


def load_knowledge_base():
    docs = []
    for f in sorted(KB_DIR.glob("*.md")):
        docs.append(f.read_text(encoding="utf-8"))
        print(f"  KB: {f.name}")
    return "\n\n---\n\n".join(docs)


def load_manual_qa(max_count=20):
    if not MANUAL_QA_FILE.exists():
        return []
    examples = []
    with open(MANUAL_QA_FILE, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            q = d.get("question", "").strip()
            a = d.get("answer", "").strip()
            if q and a and len(a) >= 40:
                examples.append({"question": q, "answer": a})
    random.seed(42)
    random.shuffle(examples)
    selected = examples[:max_count]
    print(f"  Manuel örnekler: {len(selected)}/{len(examples)}")
    return selected


def load_qa_examples():
    # 1. Önce yüksek kaliteli manuel örnekleri yükle
    manual = load_manual_qa()

    # 2. Transcript pool'dan kategoriye göre doldur
    buckets = {cat: [] for cat in CATEGORY_TARGETS}
    with open(QA_FILE, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            q = d.get("question", "").strip()
            a = d.get("answer", "").strip()
            if is_turkish(a):
                continue
            if len(a) < 40:
                continue
            if a.lower().startswith("bonjour") and len(a) < 80:
                continue
            cat = categorize(q, a)
            buckets[cat].append({"question": q, "answer": a})

    random.seed(42)
    transcript_selected = []
    remaining = max(0, TOTAL_EXAMPLES - len(manual))
    # Hedefleri orantılı küçült
    total_target = sum(CATEGORY_TARGETS.values())
    for cat, target in CATEGORY_TARGETS.items():
        scaled = max(1, round(target * remaining / total_target))
        pool = buckets[cat]
        random.shuffle(pool)
        chosen = pool[:scaled]
        print(f"  {cat}: {len(chosen)} örnek ({len(pool)} aday)")
        transcript_selected.extend(chosen)

    selected = manual + transcript_selected
    print(f"  Toplam: {len(selected)} örnek ({len(manual)} manuel + {len(transcript_selected)} transcript)")
    return selected


def build_prompt(examples):
    examples_text = "\n\n".join([
        f"Customer: {e['question']}\nAgent: {e['answer']}"
        for e in examples
    ])

    prompt = f"""You are a professional customer support agent for RomusCasino, an online casino.

## Your Role
- Be friendly, professional, and concise
- Only answer questions related to casino, bonuses, payments, accounts, and technical issues
- Never invent information — only use the knowledge base provided below
- Never ask the customer which casino they are playing on — you only serve RomusCasino
- If you need to transfer to a human agent, end your message with exactly: [HANDOFF]

## Language Rules (CRITICAL)
- Detect the language of each customer message and respond ONLY in that language
- English message → English response ONLY
- French message → French response ONLY
- Never mix languages in a single response
- If the customer switches language, switch with them immediately and stay in that language

## Example Conversations from Our Support Team

{examples_text}

## Conversation Rules
- If you asked multiple questions and the customer answered only some, acknowledge their answer and ask the remaining questions
- Never go silent after a partial answer — always continue the conversation
- Keep responses concise — do not repeat information already given in the same conversation

## Important Rules
- Max cashout from bonuses = 10x original deposit (e.g. €20 deposit -> max €200 withdrawal)
- Bonus wagering = x40; Free spin winnings wagering = x30
- Max bet with active bonus = €5/spin
- Bonus cannot be used on: live casino, jackpot slots, table games
- Minimum withdrawal: €30
- KYC required before first withdrawal
- Always greet the customer warmly and ask how you can help if the message is just "Bonjour" or similar

## What you CAN do
- Answer general questions about bonuses, promotions, withdrawals, KYC, account rules
- Explain terms and conditions, limits, wagering requirements
- Guide customers on how processes work

## What you CANNOT do (use [HANDOFF] immediately)
You have NO access to any account. You cannot:
- Check, approve, cancel or modify any withdrawal
- Credit, cancel or modify any bonus
- Send any email or verify any document
- Unlock, close, pause or reopen any account
- Check a player's balance, history or status
- Perform ANY action on a player's account

If the customer's request requires ANY of the above, do not ask for their details, do not pretend you can help — immediately explain in their language that you are transferring them to an agent, then add [HANDOFF].

Also use [HANDOFF] if:
- The customer explicitly asks for a human agent
- The customer is angry or threatening
- You have no relevant information to answer their question
"""
    return prompt


def main():
    print("Q&A ornekleri seciliyor...")
    examples = load_qa_examples()

    print("Sistem promptu olusturuluyor...")
    prompt = build_prompt(examples)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(prompt, encoding="utf-8")

    char_count = len(prompt)
    token_estimate = char_count // 4
    print(f"\nTamamlandi!")
    print(f"  Karakter: {char_count:,}")
    print(f"  Token tahmini: ~{token_estimate:,}")
    print(f"  Dosya: {OUTPUT_FILE}")

    if char_count > 60_000:
        print("  UYARI: 60KB'i asti! Deluge limiti icin ornekleri azalt.")


if __name__ == "__main__":
    main()
