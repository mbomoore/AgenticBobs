"""AI helpers for Ollama chat and BPMN extraction.

- Uses httpx to converse with a local Ollama server.
- Provides safe extraction of BPMN XML from model outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
import re

import httpx
from cytoolz import curry
from icecream import ic


DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gpt-oss:20b"


@dataclass
class OllamaConfig:
    base_url: str = DEFAULT_OLLAMA_URL
    model: str = DEFAULT_MODEL
    timeout: float = 120.0


def _client(base_url: str, timeout: float) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=timeout)


def chat(
    messages: Iterable[dict],
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 120.0,
    stream: bool = False,
) -> str:
    """Call Ollama chat API and return assistant message text.

    Parameters
    - messages: list of {role, content}
    - model/base_url/timeout: ollama connection
    - stream: if True, request streamed responses and concatenate

    Returns
    - assistant text (str)
    """
    url = "/api/chat"
    payload = {"model": model, "messages": list(messages), "stream": stream}
    ic("ollama.chat", payload)
    with _client(base_url, timeout) as c:
        if not stream:
            r = c.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("message", {}).get("content", "")
        else:
            # Stream chunks, join content. Ollama sends JSON per line.
            with c.stream("POST", url, json=payload) as r:
                r.raise_for_status()
                parts: list[str] = []
                for line in r.iter_lines():
                    if not line:
                        continue
                    try:
                        obj = httpx.Response(200, text=line).json()
                    except Exception:
                        # Fallback: ignore non-JSON
                        continue
                    msg = obj.get("message") or {}
                    content = msg.get("content")
                    if content:
                        parts.append(content)
                return "".join(parts)


BPMN_XML_RE = re.compile(r"<definitions[\s\S]*?</definitions>", re.IGNORECASE)


def extract_bpmn_xml(text: str) -> Optional[str]:
    """Extracts a BPMN <definitions>...</definitions> block from text.

    - Returns the first match or None.
    - Tolerates content before/after.
    """
    if not text:
        return None
    m = BPMN_XML_RE.search(text)
    if m:
        return m.group(0)
    return None


@curry
def system_prompt(instructions: str, bpmn_xml: str) -> list[dict]:
    """Build system + user messages for the chat model.

    Returns list of messages ready for Ollama chat endpoint.
    """
    sys_msg = {
        "role": "system",
        "content": (
            "You are a process improvement consultant and BPMN expert. Modify the provided BPMN 2.0 XML to match the user's intent. "
            "Output a single message with TWO parts in this exact order: (1) a single valid <definitions>...</definitions> block containing the updated BPMN; "
            "(2) exactly three thoughtful follow-up questions to clarify requirements, each on its own line and prefixed with Q1:, Q2:, Q3:. "
            "Do not use markdown fences or prose outside those parts. If the request is ambiguous, make a reasonable assumption and proceed."
        ),
    }
    user_msg = {
        "role": "user",
        "content": f"Current BPMN model:\n\n{bpmn_xml}\n\nInstructions: {instructions}",
    }
    return [sys_msg, user_msg]
