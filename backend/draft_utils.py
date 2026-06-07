import re

SEPARATOR = "------------------------"

COMMENT_BLOCK_PATTERN = re.compile(r"^komentarz_(\d{3}):?$", re.MULTILINE)


def strip_frontmatter(content):
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    return parts[2]


def has_comment_blocks(comments_part: str) -> bool:
    return bool(COMMENT_BLOCK_PATTERN.search(comments_part or ""))


def parse_comment_blocks(comments_part: str) -> list[dict]:
    if not comments_part.strip():
        return []

    matches = list(COMMENT_BLOCK_PATTERN.finditer(comments_part))
    blocks = []

    for i, match in enumerate(matches):
        comment_id = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(comments_part)
        body = comments_part[start:end].strip()
        if body:
            line_id = match.group(0)
            blocks.append({
                "id": line_id,
                "text": f"{line_id}\n{body}",
            })

    return blocks


def extract_draft_parts(content):
    body = strip_frontmatter(content)
    if SEPARATOR in body:
        text_part, comments_part = body.split(SEPARATOR, 1)
    else:
        text_part = body
        comments_part = ""
    return text_part.strip(), comments_part.strip()
