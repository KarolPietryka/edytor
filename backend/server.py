import os
import re
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from ai_loop import run_ai_loop
from draft_utils import SEPARATOR as DRAFT_SEPARATOR
from draft_utils import extract_draft_parts, has_comment_blocks
from env_config import is_debug, load_dotenv

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = Path(os.environ.get("EDYTOR_ROOT", str(BASE_DIR.parent)))
ENV_FILE = load_dotenv(WORKSPACE_ROOT)

app = Flask(__name__)
CORS(app)
DATA_DIR = Path(os.environ.get("EDYTOR_DATA", str(BASE_DIR / "data")))
DRAFTS_DIR = DATA_DIR / "drafts"
TEMPLATE_AI_PATH = DATA_DIR / "template_ai.md"
FILE_PATTERN = re.compile(r"^(\d{2})_(\d{4}_\d{2}_\d{2})\.md$")
CONV_PATTERN = re.compile(r"conversation:\s*(\d{3})_(\d{4}_\d{2}_\d{2})")
COMMENT_PATTERN = re.compile(r"^komentarz_(\d{3}):?$", re.MULTILINE)
SEPARATOR = DRAFT_SEPARATOR


def today_str():
    return date.today().strftime("%Y_%m_%d")


def latest_draft_in_dir():
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    latest = None
    for path in DRAFTS_DIR.glob("*.md"):
        match = FILE_PATTERN.match(path.name)
        if not match:
            continue
        ver = int(match.group(1))
        file_day = match.group(2)
        if latest is None or (file_day, ver) > latest:
            latest = (file_day, ver)
    return latest


def latest_draft_path():
    latest = latest_draft_in_dir()
    if not latest:
        return None
    file_day, ver = latest
    return DRAFTS_DIR / f"{ver:02d}_{file_day}.md"


def latest_draft_path_for_ai():
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    best_any = None
    best_with_comments = None

    for path in DRAFTS_DIR.glob("*.md"):
        match = FILE_PATTERN.match(path.name)
        if not match:
            continue
        key = (match.group(2), int(match.group(1)))
        if best_any is None or key > best_any[0]:
            best_any = (key, path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        _, comments_part = extract_draft_parts(content)
        if has_comment_blocks(comments_part):
            if best_with_comments is None or key > best_with_comments[0]:
                best_with_comments = (key, path)

    if best_with_comments:
        return best_with_comments[1]
    return best_any[1] if best_any else None


def last_conversation_for_date(day):
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    max_conv = -1
    for path in DRAFTS_DIR.glob(f"*_{day}.md"):
        try:
            head = path.read_text(encoding="utf-8")[:300]
        except OSError:
            continue
        match = CONV_PATTERN.search(head)
        if match and match.group(2) == day:
            max_conv = max(max_conv, int(match.group(1)))
    return max_conv


def next_conversation_and_file(day):
    latest = latest_draft_in_dir()
    if latest and latest[0] == day:
        next_ver = latest[1] + 1
    else:
        next_ver = 0

    next_conv = last_conversation_for_date(day) + 1
    conversation_id = f"{next_conv:03d}_{day}"
    filename = f"{next_ver:02d}_{day}.md"
    return conversation_id, filename


def next_comment_number(text):
    max_num = 0
    for match in COMMENT_PATTERN.finditer(text):
        max_num = max(max_num, int(match.group(1)))
    return max_num + 1


def draft_path(filename):
    if not FILE_PATTERN.match(filename):
        return None
    return DRAFTS_DIR / filename


def draft_path_abs(path):
    return path.resolve().as_posix()


def build_draft_content(text, conversation_id, day):
    return f"""---
conversation: {conversation_id}
date: {day}
---

{text}

{SEPARATOR}
"""


def write_draft(text):
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    day = today_str()
    conversation_id, filename = next_conversation_and_file(day)
    path = DRAFTS_DIR / filename
    path.write_text(
        build_draft_content(text, conversation_id, day),
        encoding="utf-8",
    )
    return {
        "conversation": conversation_id,
        "file": filename,
        "path": path,
    }


def sync_draft_text(path, text):
    content = path.read_text(encoding="utf-8")
    frontmatter = ""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = f"---{parts[1]}---\n\n"

    if SEPARATOR in content:
        _, comments = content.split(SEPARATOR, 1)
    else:
        comments = ""

    new_content = f"{frontmatter}{text}\n\n{SEPARATOR}\n{comments.lstrip()}"
    path.write_text(new_content, encoding="utf-8")


def append_comment_to_file(path, comment, selection):
    content = path.read_text(encoding="utf-8")
    if SEPARATOR in content:
        header, comments = content.split(SEPARATOR, 1)
    else:
        header, comments = content, ""

    num = next_comment_number(comments)
    comment_id = f"komentarz_{num:03d}"
    block = (
        f'{comment_id}:\n'
        f'"{comment}"\n'
        f'Zastosuj go do wskazanego fragmentu oryginalnego tekstu:\n'
        f'"{selection}"\n\n'
    )

    new_content = header.rstrip() + f"\n\n{SEPARATOR}\n" + comments.lstrip() + block
    path.write_text(new_content, encoding="utf-8")
    return comment_id


@app.post("/api/draft")
def create_draft():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty text"}), 400

    try:
        result = write_draft(text)
    except OSError as err:
        return jsonify({"error": str(err)}), 500

    return jsonify({
        "ok": True,
        "conversation": result["conversation"],
        "file": result["file"],
        "draft_path": draft_path_abs(result["path"]),
    })


@app.post("/api/comment")
def add_comment():
    data = request.get_json(silent=True) or {}
    filename = (data.get("file") or "").strip()
    text = (data.get("text") or "").strip()
    comment = (data.get("comment") or "").strip()
    selection = (data.get("selection") or "").strip()
    if not comment or not selection:
        return jsonify({"error": "missing fields"}), 400

    created = False
    conversation_id = None

    if filename:
        path = draft_path(filename)
        if not path:
            return jsonify({"error": "invalid file"}), 400
        if not path.exists():
            if not text:
                return jsonify({"error": "file not found"}), 404
            result = write_draft(text)
            path = result["path"]
            filename = result["file"]
            conversation_id = result["conversation"]
            created = True
    else:
        if not text:
            return jsonify({"error": "missing text"}), 400
        result = write_draft(text)
        path = result["path"]
        filename = result["file"]
        conversation_id = result["conversation"]
        created = True

    if text and not created:
        sync_draft_text(path, text)

    comment_id = append_comment_to_file(path, comment, selection)

    response = {
        "ok": True,
        "comment_id": comment_id,
        "file": filename,
        "draft_path": draft_path_abs(path),
    }
    if created:
        response["created"] = True
        response["conversation"] = conversation_id

    return jsonify(response)


@app.post("/api/ai")
def generate_ai():
    data = request.get_json(silent=True) or {}
    wytyczne = (data.get("wytyczne") or "").strip()

    draft_path = latest_draft_path_for_ai()
    if not draft_path:
        return jsonify({"error": "no draft files"}), 404

    if not TEMPLATE_AI_PATH.exists():
        return jsonify({"error": "template not found"}), 500

    try:
        draft_content = draft_path.read_text(encoding="utf-8")
        template = TEMPLATE_AI_PATH.read_text(encoding="utf-8")
        result = run_ai_loop(
            draft_content,
            template,
            DATA_DIR,
            WORKSPACE_ROOT,
            debug=is_debug(),
            wytyczne=wytyczne,
        )
    except OSError as err:
        return jsonify({"error": str(err)}), 500
    except Exception as err:
        return jsonify({"error": str(err)}), 500

    if not result.get("ok"):
        return jsonify({
            "error": result.get("error", "ai loop failed"),
            "steps": result.get("steps", []),
            "source": draft_path.name,
        }), 503

    final_text = result.get("final_text", "")
    draft_result = write_draft(final_text)

    return jsonify({
        "ok": True,
        "source": draft_path.name,
        "file": result.get("file"),
        "draft_file": draft_result["file"],
        "draft_path": draft_path_abs(draft_result["path"]),
        "text": final_text,
        "total": result.get("total", 0),
        "steps": result.get("steps", []),
        "debug": result.get("debug", False),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True, use_reloader=False)
