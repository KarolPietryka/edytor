import re
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DRAFTS_DIR = BASE_DIR / "data" / "drafts"

FILE_PATTERN = re.compile(r"^(\d{2})_(\d{4}_\d{2}_\d{2})\.md$")
CONV_PATTERN = re.compile(r"conversation:\s*(\d{3})_(\d{4}_\d{2}_\d{2})")


def today_str():
    return date.today().strftime("%Y_%m_%d")


def last_version_for_date(day):
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    max_ver = -1
    for path in DRAFTS_DIR.glob("*.md"):
        match = FILE_PATTERN.match(path.name)
        if match and match.group(2) == day:
            max_ver = max(max_ver, int(match.group(1)))
    return max_ver


def last_conversation_for_date(day):
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    max_conv = -1
    for path in DRAFTS_DIR.glob(f"*_{day}.md"):
        head = path.read_text(encoding="utf-8")[:300]
        match = CONV_PATTERN.search(head)
        if match and match.group(2) == day:
            max_conv = max(max_conv, int(match.group(1)))
    return max_conv


def next_conversation_and_file(day):
    next_conv = last_conversation_for_date(day) + 1
    next_ver = last_version_for_date(day) + 1
    conversation_id = f"{next_conv:03d}_{day}"
    filename = f"{next_ver:02d}_{day}.md"
    return conversation_id, filename


@app.post("/api/draft")
def create_draft():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "empty text"}), 400

    day = today_str()
    conversation_id, filename = next_conversation_and_file(day)

    content = f"""---
conversation: {conversation_id}
date: {day}
---

{text}
"""

    path = DRAFTS_DIR / filename
    path.write_text(content, encoding="utf-8")

    return jsonify({
        "ok": True,
        "conversation": conversation_id,
        "file": filename,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
