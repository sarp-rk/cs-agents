import os
import json
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
SCREEN_NAME   = os.getenv("ZOHO_SCREEN_NAME")
API_BASE      = f"https://salesiq.zoho.eu/api/v2/{SCREEN_NAME}"
ACCOUNTS_URL  = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.eu")

SUPABASE_URL  = os.getenv("SUPABASE_URL")
SUPABASE_KEY  = os.getenv("SUPABASE_SERVICE_KEY")
SB_HEADERS    = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates",
}

# Campaign detection
CAMPAIGN_KEYWORDS = [
    "ruby vegas", "ruby casino", "rubyvegas", "rubycasino",
    "romus casino", "romuscasino",
    "captain slots", "captainslots",
    "affiliate",
]


def is_campaign_conversation(messages):
    """Return True if any message contains a campaign keyword."""
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        text = (msg.get("message", {}).get("text", "") or "").lower()
        if any(kw in text for kw in CAMPAIGN_KEYWORDS):
            return True
    return False


# Rate limiter
RATE_LOCK          = threading.Lock()
LAST_REQUEST_TIME  = [0.0]
MIN_INTERVAL       = 0.75

# Token
TOKEN_LOCK        = threading.Lock()
CURRENT_TOKEN     = [None]
TOKEN_EXPIRES_AT  = [0.0]


# ── Zoho auth ────────────────────────────────────────────────
def get_access_token():
    resp = requests.post(f"{ACCOUNTS_URL}/oauth/v2/token", data={
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def token():
    with TOKEN_LOCK:
        if time.time() > TOKEN_EXPIRES_AT[0] - 60:
            CURRENT_TOKEN[0]    = get_access_token()
            TOKEN_EXPIRES_AT[0] = time.time() + 3600
        return CURRENT_TOKEN[0]


def rate_limited_get(url, params=None):
    with RATE_LOCK:
        elapsed = time.time() - LAST_REQUEST_TIME[0]
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        LAST_REQUEST_TIME[0] = time.time()
    headers = {"Authorization": f"Zoho-oauthtoken {token()}"}
    return requests.get(url, headers=headers, params=params, timeout=30)


# ── Supabase helpers ─────────────────────────────────────────
def sb_get_existing_ids():
    """Supabase'deki tüm conv_id'leri döndür."""
    existing = set()
    offset = 0
    limit  = 1000
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/transcripts",
            headers=SB_HEADERS,
            params={"select": "conv_id", "limit": limit, "offset": offset},
        )
        rows = r.json()
        if not rows:
            break
        for row in rows:
            existing.add(row["conv_id"])
        if len(rows) < limit:
            break
        offset += limit
    return existing


def sb_insert_transcript(conv_id, meta, qa_pairs, is_campaign=False):
    """Transcript meta + Q&A çiftlerini Supabase'e yaz."""
    # transcripts tablosu
    requests.post(
        f"{SUPABASE_URL}/rest/v1/transcripts",
        headers=SB_HEADERS,
        json={
            "conv_id":     conv_id,
            "language":    meta.get("language"),
            "brand":       _detect_brand(meta),
            "duration_ms": int(meta.get("chat_duration", 0) or 0),
            "processed":   True,
        },
    )

    # qa_pairs tablosu
    if qa_pairs:
        rows = [
            {
                "conv_id":     conv_id,
                "question":    p["question"],
                "answer":      p["answer"],
                "language":    meta.get("language"),
                "is_campaign": is_campaign,
            }
            for p in qa_pairs
        ]
        requests.post(
            f"{SUPABASE_URL}/rest/v1/qa_pairs",
            headers=SB_HEADERS,
            json=rows,
        )


def _detect_brand(meta):
    app = (meta.get("app_name") or "").lower()
    if "captain" in app:
        return "captain"
    return "romus"


# ── Q&A extraction (aynı mantık 2_process_data.py'dan) ───────
MIN_VISITOR_LEN = 10
MIN_AGENT_LEN   = 20


def extract_qa_pairs(messages, conv_id):
    pairs        = []
    visitor_msgs = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        sender_type = msg.get("sender", {}).get("type", "")
        msg_type    = msg.get("type", "")
        text        = (msg.get("message", {}).get("text", "") or "").strip()
        if msg_type != "text" or not text:
            continue
        if sender_type == "visitor":
            visitor_msgs.append(text)
        elif sender_type == "operator":
            if visitor_msgs and len(text) >= MIN_AGENT_LEN:
                q = " | ".join(visitor_msgs)
                if len(q) >= MIN_VISITOR_LEN:
                    pairs.append({"conv_id": conv_id, "question": q, "answer": text})
                visitor_msgs = []
    return pairs


# ── Fetch single conversation ────────────────────────────────
def fetch_and_store(conv_id):
    try:
        resp = rate_limited_get(f"{API_BASE}/conversations/{conv_id}/messages")
        if resp.status_code == 404:
            return conv_id, "not_found"
        resp.raise_for_status()
        data     = resp.json()
        messages = data.get("data", [])
        meta     = data.get("meta", {})
        pairs    = extract_qa_pairs(messages, conv_id)
        campaign = is_campaign_conversation(messages)
        sb_insert_transcript(conv_id, meta, pairs, is_campaign=campaign)
        label = "campaign" if campaign else f"saved ({len(pairs)} qa)"
        return conv_id, label
    except Exception as e:
        return conv_id, f"error: {e}"


# ── Main ─────────────────────────────────────────────────────
def fetch_all_conversation_ids():
    ids  = []
    page = 1
    print("Konuşma listesi alınıyor...")
    while True:
        resp = rate_limited_get(f"{API_BASE}/conversations", params={
            "status": "attended", "limit": 99, "page": page
        })
        data = resp.json().get("data", [])
        if not data:
            break
        for conv in data:
            ids.append(conv.get("id"))
        print(f"  Sayfa {page}: {len(data)} konuşma ({len(ids)} toplam)")
        page += 1
    return ids


def main():
    print("Token alınıyor...")
    CURRENT_TOKEN[0]    = get_access_token()
    TOKEN_EXPIRES_AT[0] = time.time() + 3600

    all_ids  = fetch_all_conversation_ids()
    print(f"\nToplam {len(all_ids)} attended konuşma.")

    print("Supabase'deki mevcut ID'ler kontrol ediliyor...")
    existing = sb_get_existing_ids()
    pending  = [cid for cid in all_ids if cid not in existing]
    print(f"{len(existing)} zaten var, {len(pending)} yeni.\n")

    if not pending:
        print("Yeni konuşma yok.")
        return

    saved  = 0
    errors = 0
    start  = time.time()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_and_store, cid): cid for cid in pending}
        for i, future in enumerate(as_completed(futures), 1):
            conv_id, status = future.result()
            if status.startswith("saved"):
                saved += 1
            elif status.startswith("error"):
                errors += 1
                print(f"  Hata {conv_id}: {status}")
            if i % 50 == 0:
                elapsed   = time.time() - start
                rate      = i / elapsed * 60
                remaining = (len(pending) - i) / (rate / 60) if rate > 0 else 0
                print(f"  {saved}/{len(pending)} kaydedildi | {rate:.0f}/dk | ~{remaining/60:.1f} dk kaldı")

    print(f"\nTamamlandı! {saved} yeni transcript, {errors} hata.")


if __name__ == "__main__":
    main()
