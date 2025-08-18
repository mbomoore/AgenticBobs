"""AI helpers for Ollama chat and BPMN extraction with Marvin agent framework.

- Uses httpx to converse with a local Ollama server.
- Provides safe extraction of BPMN XML from model outputs.
- Uses Marvin for agentic behavior and tool calling.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Dict, Callable, Any
import re
import json
import os

import httpx
from cytoolz import curry
from icecream import ic
import marvin


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
                        obj = json.loads(line)
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


SYSTEM_TEXT_BASE = (
    "You are a process improvement consultant and BPMN expert agent. Your job is to modify BPMN 2.0 XML to match the user's intent. "
    "Output a single message with TWO parts in this exact order: (1) a single valid <definitions>...</definitions> block containing the updated BPMN; "
    "(2) exactly three thoughtful follow-up questions to clarify requirements, each on its own line and prefixed with Q1:, Q2:, Q3:. "
    "Do not use markdown fences or prose outside those parts. If the request is ambiguous, make a reasonable assumption and proceed. "
    "I will automatically validate your BPMN and provide feedback if there are errors, so focus on creating correct, well-formed BPMN."
)

SYSTEM_TEXT_AGENT = (
    "You are an advanced BPMN agent with automatic validation capabilities. "
    "Your task is to modify BPMN 2.0 XML to match user requirements while ensuring it validates correctly. "
    "Output format: (1) Valid <definitions>...</definitions> BPMN XML block; "
    "(2) Three follow-up questions prefixed Q1:, Q2:, Q3:. "
    "I will automatically validate your BPMN output. If there are validation errors, I will provide feedback and you should fix them. "
    "Focus on creating syntactically correct BPMN with proper node references and flow connections."
)


def _build_messages(instructions: str, bpmn_xml: str, system_text: str) -> list[dict]:
    """Return a standard [system, user] message list for BPMN editing.

    Args:
        instructions: Natural language request describing desired changes.
        bpmn_xml: Current BPMN XML string.
        system_text: Instruction text for the system role.
    """
    sys_msg = {"role": "system", "content": system_text}
    user_msg = {
        "role": "user",
        "content": f"Current BPMN model:\n\n{bpmn_xml}\n\nInstructions: {instructions}",
    }
    return [sys_msg, user_msg]


@curry
def system_prompt(instructions: str, bpmn_xml: str) -> list[dict]:
    """Build system + user messages for the chat model (standard mode)."""
    return _build_messages(instructions, bpmn_xml, SYSTEM_TEXT_BASE)


@curry 
def agent_system_prompt(instructions: str, bpmn_xml: str) -> list[dict]:
    """Build system + user messages for agent mode with validation awareness."""
    return _build_messages(instructions, bpmn_xml, SYSTEM_TEXT_AGENT)


# Compatibility layer for existing tool system 
# Provides backwards compatibility while using Marvin underneath
_LEGACY_TOOLS: Dict[str, Callable] = {}

def register_tool(name: str):
    """Legacy decorator for backwards compatibility with existing tests."""
    def decorator(func):
        _LEGACY_TOOLS[name] = func
        return func
    return decorator

def get_available_tools() -> Dict[str, Callable]:
    """Get legacy tools for backwards compatibility."""
    # Include our Marvin-based validation function
    tools = _LEGACY_TOOLS.copy()
    tools["validate_bpmn"] = validate_bpmn
    return tools

# Legacy alias for compatibility
def validate_bpmn_tool(bpmn_xml: str) -> Dict[str, Any]:
    """Legacy wrapper for validate_bpmn function."""
    return validate_bpmn(bpmn_xml)


# BPMN validation tool - using regular function for direct validation
def validate_bpmn(bpmn_xml: str) -> Dict[str, Any]:
    """Validate a BPMN XML string and return errors/warnings.
    
    Args:
        bpmn_xml: BPMN XML string to validate
        
    Returns:
        Dict with 'errors' and 'warnings' lists
    """
    try:
        from core.adapters.bpmn import parse_bpmn
        from core.pir import validate
        
        pir = parse_bpmn(bpmn_xml.encode("utf-8"))
        report = validate(pir)
        return {
            "success": True,
            "errors": report.get("errors", []),
            "warnings": report.get("warnings", [])
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to validate BPMN: {str(e)}",
            "errors": [f"Parse error: {str(e)}"],
            "warnings": []
        }


# Marvin-compatible tool function (pass explicitly to Agent when needed)
def marvin_validate_bpmn(bpmn_xml: str) -> Dict[str, Any]:
    """BPMN validation callable for use in Marvin agent tool lists."""
    return validate_bpmn(bpmn_xml)


def _configure_marvin_for_ollama(base_url: str | None = None) -> None:
    """Configure Marvin to work with a local/OpenAI-compatible endpoint.

    Args:
        base_url: If provided, set OPENAI_BASE_URL to this value; otherwise
                  default to the standard local Ollama OpenAI-compatible path.
    """
    os.environ.setdefault("OPENAI_API_KEY", "dummy-key")  # Ollama doesn't need real key
    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url
    else:
        os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:11434/v1")


def _normalize_model_for_marvin(model: str) -> str:
    """Return a Marvin-friendly model string.

    - If model has a known provider prefix, return as-is.
    - Otherwise, assume OpenAI-compatible provider and prefix with 'openai:'.
    This lets us pass raw Ollama model ids like 'llama3.1:8b'.
    """
    if not isinstance(model, str) or not model:
        return model
    provider = model.split(":", 1)[0]
    known = {
        "openai", "deepseek", "azure", "openrouter", "vercel", "grok",
        "moonshotai", "fireworks", "together", "heroku", "github",
        "google-gla", "google-vertex", "vertexai", "groq", "mistral",
        "anthropic", "bedrock", "huggingface",
    }
    if provider in known:
        return model
    # If it already starts with typical OpenAI names, Marvin will infer, but for
    # custom/local names (e.g., 'llama3.1:8b' or 'gpt-oss:20b'), prefix 'openai:'.
    return f"openai:{model}"


def _extract_user_and_system_text(messages: Iterable[dict]) -> tuple[str, list[str]]:
    """Extract user content and system texts from a chat message list."""
    user_content = ""
    sys_texts: list[str] = []
    for msg in messages:
        if msg.get("role") == "user":
            user_content += msg.get("content", "") + "\n"
        elif msg.get("role") == "system" and msg.get("content"):
            sys_texts.append(msg["content"])
    return user_content, sys_texts


def agent_chat(
    messages: Iterable[dict],
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 120.0,
    max_iterations: int = 5,
) -> str:
    """Agent chat using Marvin for BPMN validation and tool use only.

    Always uses a Marvin Agent configured for BPMN validation. No legacy
    fallback is provided. If Marvin fails, the exception will propagate.
    """
    messages = list(messages)

    _configure_marvin_for_ollama(
        base_url=(base_url.rstrip("/") + "/v1") if base_url and not base_url.endswith("/v1") else base_url
    )

    # Extract the user's request and any system guidance from messages
    user_content, sys_texts = _extract_user_and_system_text(messages)
    base_guidance = (
        "You are a BPMN validation expert. Your task is to modify BPMN 2.0 XML to match user requirements while ensuring it validates correctly.\n\n"
        "Output format: (1) a single valid <definitions>...</definitions> BPMN XML block; (2) exactly three follow-up questions, one per line, prefixed Q1:, Q2:, Q3:.\n"
        "Do not include any other prose or markdown fences."
    )
    merged_instructions = ("\n\n".join(sys_texts + [base_guidance])) if sys_texts else base_guidance

    # Create a Marvin Agent without tools by default for stability across versions
    # Optionally enable tools via env toggle for tests/integration
    tools: list[Callable[..., Any]] | None
    if os.getenv("MARVIN_ENABLE_TOOLS", "").strip() not in {"", "0", "false", "False"}:
        tools = [marvin_validate_bpmn]
    else:
        tools = []

    # Create a Marvin Agent
    bpmn_agent = marvin.Agent(  # type: ignore[arg-type]
        name="bpmn_validator",
        model=_normalize_model_for_marvin(model),  # type: ignore[arg-type]
        instructions=merged_instructions,
        tools=tools,
    )

    # Use the Agent directly
    response = bpmn_agent.run(user_content)
    # Enforce presence of three Q lines to meet output contract
    response = _ensure_followup_questions(response)
    ic("Marvin agent response", response)
    return response


def _ensure_followup_questions(text: str) -> str:
    """Ensure exactly three Q1/Q2/Q3 follow-up lines exist. If missing, append generic ones."""
    if not isinstance(text, str):
        return text
    have_q1 = re.search(r"^Q1:\s*", text, flags=re.M) is not None
    have_q2 = re.search(r"^Q2:\s*", text, flags=re.M) is not None
    have_q3 = re.search(r"^Q3:\s*", text, flags=re.M) is not None
    if have_q1 and have_q2 and have_q3:
        return text
    questions = []
    if not have_q1:
        questions.append("Q1: Are task names and IDs acceptable as generated, or do you have preferred naming?")
    if not have_q2:
        questions.append("Q2: Should the process be executable (add gateways/events) or remain a high-level sketch?")
    if not have_q3:
        questions.append("Q3: Are there additional validations or constraints (SLAs, data objects) to include?")
    sep = "\n" if text and not text.endswith("\n") else ""
    return f"{text}{sep}" + "\n".join(questions)


# Note: The previous traditional validation loop has been removed intentionally.


