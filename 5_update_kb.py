"""
5_update_kb.py — Q&A pairs -> KB chunks (Supabase)

Son N günün yeni Q&A çiftlerini alır, alt kategorilere göre gruplar,
Claude ile KB chunk'larını oluşturur/günceller.
"""
import os
import sys
import requests
import anthropic
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
SB_HEADERS   = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "resolution=merge-duplicates",
}

client = anthropic.Anthropic()

LOOKBACK_DAYS       = 90   # 30 → 90 gün
MIN_ANSWER_LEN      = 40
MAX_QA_PER_CATEGORY = 50

TURKISH_CHARS = set("şğıçöüŞĞİÇÖÜ")

# Alt kategoriler: her biri kendi keyword listesiyle eşleşiyor
# Öncelik sırası önemli — daha spesifik olanlar üstte
CATEGORIES = {
    # ── BONUS ──────────────────────────────────────────────────
    "bonus_nodep_freespins": [
        "30 tours gratuit", "30 free spin", "tours gratuits inscription", "bonus sans dépôt",
        "no deposit", "sans dépôt", "free spins inscription", "tours offerts inscription",
        "tours d'inscription", "bonus inscription", "offre inscription",
    ],
    "bonus_survey_spins": [
        "enquête", "sondage", "survey", "20 tours gratuit", "20 free spin",
        "répondu à l'enquête", "tours enquête",
    ],
    "bonus_birthday": [
        "anniversaire", "birthday", "cadeau anniversaire", "bonus anniversaire",
    ],
    "bonus_welcome_pack": [
        "bienvenue", "welcome", "premier dépôt", "1er dépôt", "deuxième dépôt",
        "2ème dépôt", "3ème dépôt", "pack bienvenue", "offre de bienvenue",
        "bonus de bienvenue", "200%", "100%", "welcome pack",
    ],
    "bonus_happy_hour": [
        "happy hour", "heure bonus", "4h30", "minuit", "horaire bonus",
    ],
    "bonus_weekly_promos": [
        "mardi", "vendredi", "samedi", "lupa", "senate", "weekend legion",
        "promotion hebdomadaire", "reload", "rechargement",
    ],
    "bonus_activation": [
        "activer le bonus", "activer mon bonus", "comment activer", "où est mon bonus",
        "je ne vois pas mon bonus", "bonus pas crédité", "bonus introuvable",
        "bonus n'apparaît pas", "bonus non reçu", "pas reçu le bonus",
    ],
    "bonus_wagering": [
        "wagering", "mise", "condition de mise", "x40", "x30", "conditions de retrait",
        "débloquer le bonus", "exigences de mise",
    ],
    "bonus_max_cashout": [
        "max cashout", "retrait maximum", "gain maximum", "10x", "montant maximum",
        "combien puis-je retirer", "limite de gain", "plafond de retrait",
    ],
    "bonus_eligible_games": [
        "live casino bonus", "blackjack bonus", "roulette bonus", "jeux autorisés",
        "jeux interdits", "jackpot bonus", "quels jeux", "jouer avec bonus",
        "table games bonus",
    ],
    "bonus_removal": [
        "supprimer le bonus", "annuler le bonus", "retirer le bonus", "enlever le bonus",
        "retrait sans bonus", "sans utiliser le bonus",
    ],
    "bonus_cancellation_rules": [
        "bonus annulé", "bonus supprimé", "bonus perdu", "pourquoi bonus annulé",
        "multi-compte", "vpn bonus", "abus bonus", "fraude bonus",
    ],
    "bonus_loss_request": [
        "bonus pour mes pertes", "compensation perte", "j'ai perdu", "remboursement perte",
        "bonus perte", "bonus fidélité", "bonus rechargement demande",
    ],

    # ── WITHDRAWAL ─────────────────────────────────────────────
    "withdrawal_process": [
        "comment faire un retrait", "effectuer un retrait", "procédure retrait",
        "étapes retrait", "comment retirer", "faire un virement",
    ],
    "withdrawal_pending": [
        "retrait en attente", "retrait pending", "retrait pas arrivé", "où est mon retrait",
        "retrait pas reçu", "retrait bloqué", "délai retrait", "quand retrait",
        "retrait long", "retrait pas traité",
    ],
    "withdrawal_limits": [
        "minimum retrait", "maximum retrait", "limite retrait", "plafond retrait",
        "30 euros retrait", "1500 euros", "7500 euros", "15000 euros",
    ],
    "withdrawal_deposit_issue": [
        "dépôt pas reçu", "dépôt en attente", "dépôt pas crédité", "dépôt non reçu",
        "argent pas sur compte", "dépôt bloqué", "transaction pending",
    ],

    # ── KYC ────────────────────────────────────────────────────
    "kyc_documents": [
        "quels documents", "pièces à fournir", "justificatif", "document identité",
        "passeport", "carte d'identité", "rib", "relevé bancaire",
        "preuve d'adresse", "facture", "document bancaire", "source de fonds",
    ],
    "kyc_payment_ownership": [
        "propriété méthode de paiement", "payment method ownership",
        "preuve carte", "carte bancaire photo", "justificatif carte",
        "document carte bancaire",
    ],
    "kyc_process": [
        "comment envoyer documents", "où envoyer documents", "vérification compte",
        "validation compte", "compte vérifié", "kyc en cours",
    ],
    "kyc_pending": [
        "documents en attente", "documents pas validés", "vérification en cours",
        "combien de temps validation", "délai documents", "documents toujours en attente",
    ],
    "kyc_address_mismatch": [
        "déménagé", "ancienne adresse", "adresse pas à jour", "changement adresse",
    ],

    # ── ACCOUNT ────────────────────────────────────────────────
    "account_registration": [
        "inscription", "créer un compte", "s'inscrire", "nouveau joueur",
        "ouvrir un compte", "enregistrement",
    ],
    "account_email_issue": [
        "mail de confirmation", "email pas reçu", "mail de validation", "lien activation",
        "activer le compte", "mail introuvable", "adresse mail", "changer email",
    ],
    "account_login": [
        "connexion impossible", "ne peut pas se connecter", "mot de passe oublié",
        "login problème", "accès compte", "compte bloqué connexion",
    ],
    "account_phone_geo": [
        "numéro de téléphone invalide", "france interdit", "restriction pays",
        "juridiction", "pays bloqué", "vpn inscription", "joueur français",
    ],
    "account_duplicate": [
        "compte déjà existant", "déjà inscrit", "multi-compte", "deux comptes",
        "compte en double",
    ],
    "account_closure": [
        "fermer compte", "clôturer compte", "supprimer compte", "fermeture définitive",
        "arrêter de jouer",
    ],
    "account_reactivation": [
        "rouvrir compte", "réactiver compte", "compte fermé réouvrir",
        "reprendre jeu", "débloquer compte",
    ],
    "account_self_exclusion": [
        "self-exclusion", "auto-exclusion", "pause", "time-out", "limite dépôt",
        "jeu responsable", "moi-même exclure", "reprendre après pause",
    ],
    "account_dormant": [
        "compte inactif", "frais inactivité", "compte dormant", "10 euros mois",
    ],

    # ── TECHNICAL ──────────────────────────────────────────────
    "technical_game": [
        "jeu ne charge pas", "jeu bloqué", "freeze", "bug jeu", "jeu ne fonctionne pas",
        "jeu lent", "jeu plante", "erreur jeu", "chargement",
    ],
    "technical_payment": [
        "erreur dépôt", "dépôt échoué", "problème paiement", "erreur transaction",
        "paiement refusé", "carte refusée",
    ],
    "technical_login_issue": [
        "bug connexion", "erreur connexion", "site ne fonctionne pas",
        "problème technique site",
    ],

    # ── VIP ────────────────────────────────────────────────────
    "vip_how_to_join": [
        "comment devenir vip", "accès vip", "programme vip", "devenir vip",
        "invitation vip", "rejoindre vip",
    ],
    "vip_cashback": [
        "cashback", "remboursement hebdomadaire", "cashback semaine",
        "quand cashback", "montant cashback", "cashback pas reçu",
    ],
    "vip_levels": [
        "niveau vip", "tier vip", "level vip", "avantages vip", "manager vip",
        "vip level 1", "vip level 2", "vip level 3", "vip level 4",
    ],
}

# Her kategorinin odak noktası — Claude prompt'una ekleniyor
CATEGORY_FOCUS = {
    "bonus_nodep_freespins":    "no-deposit free spins at registration (30 tours gratuit), how to claim, where to find them",
    "bonus_survey_spins":       "survey/enquête free spins (20 tours), how to receive after completing survey",
    "bonus_birthday":           "birthday bonus policy — do we offer one, conditions",
    "bonus_welcome_pack":       "welcome pack details (1st/2nd/3rd deposit percentages, free spin amounts, eligible games)",
    "bonus_happy_hour":         "Happy Hour daily promotion (times, deposit amounts, free spins, no wagering)",
    "bonus_weekly_promos":      "weekly promotions: Lupa's Tuesdays, Senate's Fridays, Weekend's Legion",
    "bonus_activation":         "how to activate a bonus, where to find it in the interface, what to do if not showing",
    "bonus_wagering":           "wagering requirements (x40 deposit bonus, x30 free spins), how to complete them",
    "bonus_max_cashout":        "maximum cashout rules (10x deposit for deposit bonuses, limits by bonus type)",
    "bonus_eligible_games":     "which games are allowed with bonus (slots), which are forbidden (live, jackpot, table)",
    "bonus_removal":            "how to cancel/remove an active bonus before wagering is complete",
    "bonus_cancellation_rules": "why a bonus gets cancelled (multi-account, VPN, abusive betting, fraud)",
    "bonus_loss_request":       "player requests bonus for losses — policy, what agents say",
    "withdrawal_process":       "how to make a withdrawal, steps, processing times",
    "withdrawal_pending":       "withdrawal is pending/delayed — reasons, typical timelines, what to check",
    "withdrawal_limits":        "withdrawal limits: minimum €30, daily €1500, weekly €7500, monthly €15000",
    "withdrawal_deposit_issue": "deposit not credited, pending deposit, transaction issues",
    "kyc_documents":            "required documents: ID, proof of address, payment card, bank ownership, source of funds",
    "kyc_payment_ownership":    "payment method ownership proof — what it is, which documents are accepted",
    "kyc_process":              "how to submit documents, where to send them, verification process",
    "kyc_pending":              "documents under review — timeline, what to expect",
    "kyc_address_mismatch":     "player has moved, old address on file, what documents to provide",
    "account_registration":     "how to register, one account per person rule, required information",
    "account_email_issue":      "confirmation email not received, how to activate account, email change",
    "account_login":            "login problems, forgot password, account access issues",
    "account_phone_geo":        "phone number invalid for French players, geo-restriction, VPN usage",
    "account_duplicate":        "already have an account error, duplicate account situation",
    "account_closure":          "how to close account permanently, processing time",
    "account_reactivation":     "how to reopen a closed account",
    "account_self_exclusion":   "self-exclusion, time-out options, deposit limits, how to resume after pause",
    "account_dormant":          "dormant account fee (€10/month after 12 months inactivity)",
    "technical_game":           "game not loading, freezing, bugs — what to suggest to player",
    "technical_payment":        "deposit/payment technical errors, failed transactions",
    "technical_login_issue":    "site/connection technical problems",
    "vip_how_to_join":          "how to become VIP — invitation only, criteria",
    "vip_cashback":             "VIP cashback — percentages by level, when it's credited",
    "vip_levels":               "VIP levels 1-4, benefits at each level, dedicated manager",
}


def is_turkish(text):
    return any(c in text for c in TURKISH_CHARS)


def categorize(question, answer):
    text = (question + " " + answer).lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw in text for kw in keywords):
            return cat
    return "other"


def fetch_all_qa(since_iso: str):
    rows  = []
    offset, limit = 0, 1000
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/qa_pairs",
            headers={**SB_HEADERS, "Prefer": ""},
            params={
                "select":     "question,answer",
                "created_at": f"gte.{since_iso}",
                "limit":      limit,
                "offset":     offset,
            },
        )
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return rows


def group_by_category(qa_rows):
    buckets = {cat: [] for cat in CATEGORIES}
    for row in qa_rows:
        q, a = row.get("question", ""), row.get("answer", "")
        if is_turkish(a) or len(a) < MIN_ANSWER_LEN:
            continue
        cat = categorize(q, a)
        if cat == "other":
            continue
        if len(buckets[cat]) < MAX_QA_PER_CATEGORY:
            buckets[cat].append({"q": q, "a": a})
    return buckets


def get_existing_chunk(brand, category):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/kb_chunks",
        headers={**SB_HEADERS, "Prefer": ""},
        params={"brand": f"eq.{brand}", "category": f"eq.{category}", "select": "id,title,content"},
    )
    rows = r.json()
    return rows[0] if rows else None


def generate_embedding(text):
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "text-embedding-3-small", "input": text},
    )
    return r.json()["data"][0]["embedding"]


def upsert_chunk(brand, category, title, content, chunk_id=None):
    embedding = generate_embedding(title + "\n" + content)
    payload = {"brand": brand, "category": category, "title": title, "content": content,
                "embedding": embedding,
                "approved": False,
                "updated_at": datetime.now(timezone.utc).isoformat()}
    if chunk_id:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/kb_chunks?id=eq.{chunk_id}",
            headers=SB_HEADERS, json=payload,
        )
    else:
        requests.post(f"{SUPABASE_URL}/rest/v1/kb_chunks", headers=SB_HEADERS, json=payload)


def has_new_info(brand, category, qa_pairs, existing_content):
    """Ask Claude if new Q&A pairs contain info not already in the existing chunk."""
    if not existing_content:
        return True  # No existing chunk → always create

    focus = CATEGORY_FOCUS.get(category, category)
    qa_text = "\n\n".join([f"Visitor: {p['q']}\nAgent: {p['a']}" for p in qa_pairs])

    prompt = f"""You are reviewing a casino knowledge base for {brand.title()} Casino.
Category: {category} — {focus}

EXISTING KB CHUNK:
{existing_content}

NEW SUPPORT CONVERSATIONS:
{qa_text}

Do the new conversations contain any useful information NOT already covered in the existing chunk?
Answer with ONLY "YES" or "NO"."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip().upper().startswith("YES")


def build_kb_chunk(brand, category, qa_pairs, existing_content):
    focus = CATEGORY_FOCUS.get(category, category)
    qa_text = "\n\n".join([f"Visitor: {p['q']}\nAgent: {p['a']}" for p in qa_pairs])
    existing_section = f"\n\nExisting KB content to UPDATE (keep all useful info, add/improve):\n{existing_content}" if existing_content else ""

    prompt = f"""You are maintaining a casino customer support knowledge base for {brand.title()} Casino.
Category: {category}
Focus: {focus}
{existing_section}

New support conversations from this category:
{qa_text}

Write a detailed knowledge base section covering this specific topic in English.
Rules:
- Factual only — no invented details, only what appears in conversations or is confirmed casino policy
- Markdown format: ## title, then bullet points or short paragraphs
- Max 2000 characters total
- Be specific: include exact amounts, timeframes, steps, conditions where known
- Prioritize the most common situations agents handle

Return ONLY the markdown content."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def update_pipeline_state(key, value):
    requests.post(
        f"{SUPABASE_URL}/rest/v1/pipeline_state",
        headers={**SB_HEADERS, "Prefer": "resolution=merge-duplicates"},
        json={"key": key, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()},
    )


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-date", help="YYYY-MM-DD formatında başlangıç tarihi (default: son 90 gün)")
    args = parser.parse_args()

    if args.from_date:
        from_dt = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        from_dt = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    since_iso = from_dt.isoformat()
    print(f"Q&A çiftleri çekiliyor (from: {from_dt.date()})...")
    qa_rows = fetch_all_qa(since_iso)
    print(f"Toplam {len(qa_rows)} Q&A çifti")

    buckets = group_by_category(qa_rows)
    filled = {k: v for k, v in buckets.items() if v}
    print(f"{len(filled)}/{len(CATEGORIES)} kategori doldu\n")

    for brand in ["romus", "captain"]:
        print(f"── {brand.title()} ──")
        updated = 0

        for category, pairs in buckets.items():
            if not pairs:
                continue

            existing = get_existing_chunk(brand, category)
            existing_content = existing["content"] if existing else None
            chunk_id = existing["id"] if existing else None

            try:
                if not has_new_info(brand, category, pairs, existing_content):
                    print(f"  – {category} (yeni bilgi yok, atlandı)")
                    continue
                content = build_kb_chunk(brand, category, pairs, existing_content)
                lines   = content.strip().splitlines()
                title   = lines[0].lstrip("#").strip() if lines else f"{brand} {category}"
                upsert_chunk(brand, category, title, content, chunk_id)
                print(f"  ✓ {category} ({len(content)} karakter)")
                updated += 1
            except Exception as e:
                print(f"  ✗ {category}: {e}")

        print(f"  {updated} chunk güncellendi\n")

    update_pipeline_state("last_kb_update", datetime.now(timezone.utc).isoformat())
    print("Tamamlandı!")


if __name__ == "__main__":
    main()
