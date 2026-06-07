import re
from pathlib import Path

from ai_client import AiClientError, call_ai
from draft_utils import extract_draft_parts, parse_comment_blocks
AI_FILE_NAME = "ai.md"
AI_FILE_PATTERN = re.compile(r"^ai_(\d{3})\.md$")
FINAL_VERSION_MARKER = "Final version:"
FINAL_PLACEHOLDER = "Odpowiedz z AI. Obudz sie "
AI_FORMAT_HINT = (
    'Wprowadz zmiany i oddaj odpowiedz WYLACZNIE w tym formacie.\n'
    'W Final version wpisz TYLKO zmieniony tekst z sekcji w podwojnych cudzyslowach '
    '(tekst uzytkownika). Bez wytycznych, bez komentarzy, bez instrukcji.\n\n'
    'Final version:\n"\n<tutaj caly zmieniony tekst>\n"'
)

WYTYCZNE_LEAK_PREFIX = "Ogolne wytyczne dla Ciebie jako edytora:"


def _extract_quoted_block(chunk: str) -> str:
    chunk = chunk.lstrip()
    if chunk.startswith('"'):
        chunk = chunk[1:]
    chunk = chunk.lstrip("\r\n")

    close_idx = -1
    pos = 0
    while pos < len(chunk):
        nl = chunk.find("\n", pos)
        if nl == -1:
            break
        line_end = nl + 1
        if line_end < len(chunk) and chunk[line_end] == '"':
            tail = chunk[line_end + 1:].strip()
            if not tail:
                close_idx = nl
        pos = line_end

    if close_idx != -1:
        return chunk[:close_idx].strip()

    if chunk.endswith('"'):
        return chunk[:-1].strip()

    return chunk.strip()


def sanitize_final_text(text: str) -> str:
    t = text.strip()
    if not t:
        return t

    while t.startswith(WYTYCZNE_LEAK_PREFIX):
        end = t.find('""', len(WYTYCZNE_LEAK_PREFIX))
        if end == -1:
            break
        t = t[end + 2:].lstrip()

    while True:
        stripped = False
        for prefix in (
            "Wprowadz zmiany i oddaj odpowiedz WYLACZNIE w tym formacie:",
            FINAL_VERSION_MARKER,
        ):
            if t.lower().startswith(prefix.lower()):
                t = t[len(prefix):].lstrip()
                stripped = True
        if not stripped:
            break

    if t.startswith('"'):
        t = t[1:].lstrip("\r\n")
    if t.endswith('"'):
        t = t[:-1].rstrip()

    return t.strip()


def extract_final_version(response: str) -> str:
    """Wyciąga ostatni sensowny blok Final version z odpowiedzi AI."""
    parts = re.split(r"Final version:\s*", response, flags=re.IGNORECASE)
    if len(parts) < 2:
        return sanitize_final_text(response.strip())

    candidates = []
    for part in parts[1:]:
        block = sanitize_final_text(_extract_quoted_block(part))
        if not block:
            continue
        if "<tutaj caly zmieniony tekst>" in block.lower():
            continue
        if block.lower().startswith("odpowiedz z ai"):
            continue
        candidates.append(block)

    if candidates:
        return candidates[-1]

    return sanitize_final_text(_extract_quoted_block(parts[-1]))


def _fill_template(template: str, tekst: str, komentarz: str, wytyczne: str) -> str:
    k = komentarz if komentarz else "(brak komentarzy)"
    w = wytyczne if wytyczne else "(brak wytycznych)"
    return (
        template.replace("{tekst}", tekst)
        .replace("{komentarze}", k)
        .replace("{wytyczne}", w)
    )


def _template_body(template: str) -> str:
    if FINAL_VERSION_MARKER in template:
        return template.split(FINAL_VERSION_MARKER, 1)[0].rstrip()
    return template.rstrip()


def build_prompt_for_ai(template: str, tekst: str, komentarz: str, wytyczne: str) -> str:
    body = _fill_template(_template_body(template), tekst, komentarz, wytyczne)
    return f"{body}\n\n{AI_FORMAT_HINT}"


def build_ai_md(template: str, tekst: str, komentarz: str, wytyczne: str, final_text: str) -> str:
    body = _fill_template(_template_body(template), tekst, komentarz, wytyczne)
    return f'{body}\n\n{FINAL_VERSION_MARKER}\n"\n{final_text}\n"'


def _next_numbered_path(directory: Path, pattern: re.Pattern, prefix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    max_num = 0
    for path in directory.glob(f"{prefix}_*.md"):
        match = pattern.match(path.name)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return directory / f"{prefix}_{max_num + 1:03d}.md"


def write_ai_md(data_dir: Path, content: str, debug: bool = False) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    main_path = data_dir / AI_FILE_NAME
    main_path.write_text(content, encoding="utf-8")

    if debug:
        snap = _next_numbered_path(data_dir / "ai", AI_FILE_PATTERN, "ai")
        snap.write_text(content, encoding="utf-8")
        return snap

    return main_path


def _run_step(
    template: str,
    tekst: str,
    komentarz: str,
    wytyczne: str,
    data_dir: Path,
    workspace_root: Path,
    debug: bool,
) -> dict:
    prompt = build_prompt_for_ai(template, tekst, komentarz, wytyczne)
    placeholder_md = build_ai_md(template, tekst, komentarz, wytyczne, FINAL_PLACEHOLDER)
    write_ai_md(data_dir, placeholder_md, debug=False)

    try:
        response = call_ai(prompt, str(workspace_root))
    except AiClientError as err:
        return {"ok": False, "error": str(err)}

    final_text = extract_final_version(response)
    if not final_text.strip():
        return {"ok": False, "error": "AI zwrocilo pusty Final version"}
    if final_text.startswith(WYTYCZNE_LEAK_PREFIX):
        return {"ok": False, "error": "AI zwrocilo wytyczne zamiast tekstu — sprobuj ponownie"}

    complete_md = build_ai_md(template, tekst, komentarz, wytyczne, final_text)
    ai_path = write_ai_md(data_dir, complete_md, debug)

    return {
        "ok": True,
        "final_text": final_text,
        "file": ai_path.name,
    }


def run_ai_loop(
    draft_content: str,
    template: str,
    data_dir: Path,
    workspace_root: Path,
    debug: bool = False,
    wytyczne: str = "",
) -> dict:
    tekst, comments_part = extract_draft_parts(draft_content)
    comment_blocks = parse_comment_blocks(comments_part)

    if not comment_blocks:
        result = _run_step(
            template, tekst, "(brak komentarzy)", wytyczne, data_dir, workspace_root, debug,
        )
        if not result["ok"]:
            return {
                "ok": False,
                "error": result["error"],
                "steps": [],
                "current_text": tekst,
                "file": AI_FILE_NAME,
                "debug": debug,
            }
        return {
            "ok": True,
            "steps": [{"comment_id": None, "status": "done", "file": result["file"]}],
            "total": 0,
            "final_text": result["final_text"],
            "file": result["file"],
            "debug": debug,
        }

    current_text = tekst
    steps = []
    last_file = None

    for block in comment_blocks:
        result = _run_step(
            template, current_text, block["text"], wytyczne, data_dir, workspace_root, debug,
        )
        if not result["ok"]:
            steps.append({
                "comment_id": block["id"],
                "status": "error",
                "error": result["error"],
            })
            return {
                "ok": False,
                "error": result["error"],
                "steps": steps,
                "current_text": current_text,
                "file": AI_FILE_NAME,
                "debug": debug,
            }

        current_text = result["final_text"]
        last_file = result["file"]
        steps.append({
            "comment_id": block["id"],
            "status": "done",
            "file": result["file"],
        })

    return {
        "ok": True,
        "steps": steps,
        "total": len(comment_blocks),
        "final_text": current_text,
        "file": last_file,
        "debug": debug,
    }
