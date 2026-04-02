import json
import re
from pathlib import Path

TRANSCRIPTS_DIR = Path("data/transcripts")
OUTPUT_FILE = Path("data/qa_pairs.jsonl")

MIN_VISITOR_LEN = 10   # çok kısa mesajları atla ("Bonjour" gibi)
MIN_AGENT_LEN = 20     # çok kısa agent cevaplarını atla


def extract_qa_pairs(transcript_file):
    data = json.loads(transcript_file.read_text(encoding="utf-8"))
    messages = data.get("data", [])
    conv_id = transcript_file.stem

    pairs = []
    visitor_msgs = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        sender = msg.get("sender", {})
        sender_type = sender.get("type", "")
        msg_type = msg.get("type", "")
        text = msg.get("message", {}).get("text", "")
        if text:
            text = text.strip()

        # Sadece text mesajları al, info/system atla
        if msg_type != "text" or not text:
            continue

        if sender_type == "visitor":
            visitor_msgs.append(text)
        elif sender_type == "operator":
            if visitor_msgs and len(text) >= MIN_AGENT_LEN:
                visitor_text = " | ".join(visitor_msgs)
                if len(visitor_text) >= MIN_VISITOR_LEN:
                    pairs.append({
                        "conv_id": conv_id,
                        "question": visitor_text,
                        "answer": text,
                    })
                visitor_msgs = []

    return pairs


def main():
    files = list(TRANSCRIPTS_DIR.glob("*.json"))
    print(f"{len(files)} transcript dosyası bulundu.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    total_pairs = 0
    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        for i, f in enumerate(files):
            try:
                pairs = extract_qa_pairs(f)
                for pair in pairs:
                    out.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    total_pairs += 1
            except Exception as e:
                print(f"  Hata ({f.name}): {e}")

            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(files)} işlendi, {total_pairs} Q&A çifti")

    print(f"\nTamamlandi! {total_pairs} Q&A cifti -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
