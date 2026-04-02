"""
migrate_to_supabase.py — Mevcut lokal transcript dosyalarını Supabase'e aktar.
Tek seferlik çalıştır.
"""
import json, os, requests, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SB_HEADERS   = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "resolution=ignore-duplicates",
}

MIN_VISITOR_LEN = 10
MIN_AGENT_LEN   = 20
BATCH_SIZE      = 500   # Supabase'e toplu insert


def detect_brand(meta):
    app = (meta.get("app_name") or "").lower()
    return "captain" if "captain" in app else "romus"


def extract_qa_pairs(messages, conv_id, language):
    pairs, visitor_msgs = [], []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        sender_type = msg.get("sender", {}).get("type", "")
        text = (msg.get("message", {}).get("text", "") or "").strip()
        if msg.get("type") != "text" or not text:
            continue
        if sender_type == "visitor":
            visitor_msgs.append(text)
        elif sender_type == "operator":
            if visitor_msgs and len(text) >= MIN_AGENT_LEN:
                q = " | ".join(visitor_msgs)
                if len(q) >= MIN_VISITOR_LEN:
                    pairs.append({"conv_id": conv_id, "question": q, "answer": text, "language": language})
                visitor_msgs = []
    return pairs


def batch_insert(table, rows):
    if not rows:
        return
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=SB_HEADERS, json=rows)
    if r.status_code not in (200, 201):
        print(f"  Insert hatası {table}: {r.status_code} {r.text[:200]}")


def main():
    files = list(Path("data/transcripts").glob("*.json"))
    print(f"{len(files)} transcript dosyası bulundu")

    # Mevcut conv_id'leri çek (yeniden yüklemeyi önle)
    print("Supabase'deki mevcut ID'ler kontrol ediliyor...")
    existing = set()
    offset, limit = 0, 1000
    while True:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/transcripts",
                         headers={**SB_HEADERS, "Prefer": ""},
                         params={"select": "conv_id", "limit": limit, "offset": offset})
        rows = r.json()
        if not rows:
            break
        for row in rows:
            existing.add(row["conv_id"])
        if len(rows) < limit:
            break
        offset += limit
    print(f"{len(existing)} zaten mevcut")

    pending = [f for f in files if f.stem not in existing]
    print(f"{len(pending)} dosya aktarılacak\n")

    t_batch, qa_batch = [], []
    saved, errors = 0, 0
    start = time.time()

    for i, f in enumerate(pending):
        try:
            data     = json.loads(f.read_text(encoding="utf-8"))
            meta     = data.get("meta", {})
            messages = data.get("data", [])
            conv_id  = f.stem
            brand    = detect_brand(meta)
            language = meta.get("language")

            t_batch.append({
                "conv_id":     conv_id,
                "language":    language,
                "brand":       brand,
                "duration_ms": int(meta.get("chat_duration", 0) or 0),
                "processed":   True,
            })

            qa_batch.extend(extract_qa_pairs(messages, conv_id, language))

            if len(t_batch) >= BATCH_SIZE:
                batch_insert("transcripts", t_batch)
                batch_insert("qa_pairs",    qa_batch)
                saved += len(t_batch)
                t_batch, qa_batch = [], []

        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"  Hata ({f.name}): {e}")

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start
            pct     = (i + 1) / len(pending) * 100
            remaining = (elapsed / (i + 1)) * (len(pending) - i - 1)
            print(f"  {i+1}/{len(pending)} ({pct:.0f}%) | ~{remaining/60:.1f} dk kaldı")

    # Kalan batch
    if t_batch:
        batch_insert("transcripts", t_batch)
        batch_insert("qa_pairs",    qa_batch)
        saved += len(t_batch)

    print(f"\nTamamlandı! {saved} transcript, {errors} hata.")
    print(f"Toplam süre: {(time.time()-start)/60:.1f} dk")


if __name__ == "__main__":
    main()
