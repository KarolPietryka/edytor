import json
import os
import sys
import urllib.error
import urllib.request

if sys.version_info < (3, 12) and not hasattr(os, "get_blocking"):
    def _get_blocking(_fd):
        return True

    def _set_blocking(_fd, _blocking):
        pass

    os.get_blocking = _get_blocking
    os.set_blocking = _set_blocking


class AiClientError(Exception):
    pass


def call_openai(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise AiClientError("missing OPENAI_API_KEY")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise AiClientError(f"OpenAI HTTP {err.code}: {detail}") from err

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as err:
        raise AiClientError("invalid OpenAI response") from err


def call_cursor(prompt: str, cwd: str) -> str:
    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise AiClientError("missing CURSOR_API_KEY")

    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
    except ImportError as err:
        raise AiClientError("cursor-sdk not installed (pip install cursor-sdk)") from err
    except Exception as err:
        raise AiClientError(f"cursor-sdk import failed: {err}") from err

    model = os.environ.get("CURSOR_MODEL", "composer-2.5")
    try:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=api_key,
                model=model,
                local=LocalAgentOptions(cwd=cwd),
            ),
        )
    except Exception as err:
        raise AiClientError(f"cursor-sdk call failed: {err}") from err

    text = getattr(result, "result", None) or ""
    return str(text).strip()


def call_ai(prompt: str, cwd: str) -> str:
    if os.environ.get("CURSOR_API_KEY", "").strip():
        return call_cursor(prompt, cwd)
    if os.environ.get("OPENAI_API_KEY", "").strip():
        return call_openai(prompt)
    raise AiClientError(
        "brak klucza AI — dodaj OPENAI_API_KEY lub CURSOR_API_KEY do pliku .env w root projektu"
    )
