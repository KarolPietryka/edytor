import re
from pathlib import Path

from ai_client import AiClientError, call_ai
from draft_utils import extract_draft_parts, parse_comment_blocks
AI_FILE_NAME = "ai.md"
AI_FILE_PATTERN = re.compile(r"^ai_(\d{3})\.md$")
FINAL_VERSION_MARKER = "Final version:"
FINAL_PLACEHOLDER = "Odpowiedz z AI. Obudz sie "
AI_FORMAT_HINT = (
    'Wprowadz zmiany i oddaj odpowiedz WYLACZNIE w tym formacie:\n\n'
    'Final version:\n"\n<tutaj caly zmieniony tekst>\n"'
)

def extract_final_version(response: str) -> str:
    """Wyciąga treść z ostatniego bloku Final version (do ostatniego zamykającego \")."""
    lower = response.lower()
    marker = FINAL_VERSION_MARKER.lower()
    idx = lower.rfind(marker)
    if idx == -1:
        return response.strip()

    chunk = response[idx + len(FINAL_VERSION_MARKER):].lstrip()
    if chunk.startswith('"'):
        chunk = chunk[1:]
    chunk = chunk.lstrip("\r\n")

    last_close = chunk.rfind('\n"')
    if last_close != -1:
        return chunk[:last_close].strip()

    return chunk.strip()


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
