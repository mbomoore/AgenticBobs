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
            "You are a process improvement consultant and BPMN expert agent. Your job is to modify BPMN 2.0 XML to match the user's intent. "
            "Output a single message with TWO parts in this exact order: (1) a single valid <definitions>...</definitions> block containing the updated BPMN; "
            "(2) exactly three thoughtful follow-up questions to clarify requirements, each on its own line and prefixed with Q1:, Q2:, Q3:. "
            "Do not use markdown fences or prose outside those parts. If the request is ambiguous, make a reasonable assumption and proceed. "
            "I will automatically validate your BPMN and provide feedback if there are errors, so focus on creating correct, well-formed BPMN."
        ),
    }
    user_msg = {
        "role": "user",
        "content": f"Current BPMN model:\n\n{bpmn_xml}\n\nInstructions: {instructions}",
    }
    return [sys_msg, user_msg]


@curry 
def agent_system_prompt(instructions: str, bpmn_xml: str) -> list[dict]:
    """Enhanced system prompt for agent mode with validation awareness."""
    sys_msg = {
        "role": "system", 
        "content": (
            "You are an advanced BPMN agent with automatic validation capabilities. "
            "Your task is to modify BPMN 2.0 XML to match user requirements while ensuring it validates correctly. "
            "Output format: (1) Valid <definitions>...</definitions> BPMN XML block; "
            "(2) Three follow-up questions prefixed Q1:, Q2:, Q3:. "
            "I will automatically validate your BPMN output. If there are validation errors, I will provide feedback and you should fix them. "
            "Focus on creating syntactically correct BPMN with proper node references and flow connections."
        ),
    }
    user_msg = {
        "role": "user",
        "content": f"Current BPMN model:\n\n{bpmn_xml}\n\nInstructions: {instructions}",
    }
    return [sys_msg, user_msg]


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


# Marvin-compatible tool version for agent use
@marvin.fn
def marvin_validate_bpmn(bpmn_xml: str) -> Dict[str, Any]:
    """Marvin-compatible BPMN validation tool for use in agent workflows."""
    return validate_bpmn(bpmn_xml)


def _configure_marvin_for_ollama():
    """Configure Marvin to work with local Ollama server."""
    # Set up environment variables for Ollama compatibility
    os.environ.setdefault("OPENAI_API_KEY", "dummy-key")  # Ollama doesn't need real key
    os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:11434/v1")


def agent_chat(
    messages: Iterable[dict],
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 120.0,
    max_iterations: int = 5,
) -> str:
    """Enhanced chat that can use Marvin agents for BPMN validation.
    
    Falls back to traditional chat if Marvin is not available or fails.
    The agent will attempt to validate and fix BPMN automatically.
    """
    messages = list(messages)
    
    # Try to use Marvin agent first
    try:
        _configure_marvin_for_ollama()
        
        # Create a Marvin agent for BPMN validation
        bpmn_agent = marvin.Agent(
            name="bpmn_validator",
            model=model,
            instructions="""You are a BPMN validation expert. Your task is to modify BPMN 2.0 XML to match user requirements while ensuring it validates correctly.
            
            Output format: (1) Valid <definitions>...</definitions> BPMN XML block; (2) Three follow-up questions prefixed Q1:, Q2:, Q3:.
            
            You have access to a BPMN validation tool. Use it to check your work and fix any errors iteratively.""",
            tools=[marvin_validate_bpmn],
        )
        
        # Extract the user's request from messages
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content += msg.get("content", "") + "\n"
        
        # Use Marvin agent - this will automatically handle tool calling
        response = marvin.run(user_content, agent=bpmn_agent)
        ic("Marvin agent response", response)
        return response
        
    except Exception as e:
        ic("Marvin agent failed, falling back to traditional chat", e)
        # Fall back to original implementation with validation loop
        return _traditional_agent_chat(messages, model=model, base_url=base_url, timeout=timeout, max_iterations=max_iterations)


def _traditional_agent_chat(
    messages: Iterable[dict],
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 120.0,
    max_iterations: int = 5,
) -> str:
    """Traditional agent chat with manual validation loop as fallback."""
    messages = list(messages)
    
    for iteration in range(max_iterations):
        ic(f"Agent iteration {iteration + 1}")
        
        # Get response from model
        response = chat(messages, model=model, base_url=base_url, timeout=timeout)
        
        # Extract BPMN XML if present
        bpmn_xml = extract_bpmn_xml(response)
        
        if bpmn_xml:
            # Validate the BPMN using our validation function
            validation_result = validate_bpmn(bpmn_xml)
            
            if validation_result.get("success") and not validation_result.get("errors"):
                # BPMN is valid, return the response
                return response
            
            # BPMN has errors, provide feedback to the model
            validation_feedback = {
                "role": "system",
                "content": (
                    "The BPMN you provided has validation issues. "
                    f"Errors: {validation_result.get('errors', [])}. "
                    f"Warnings: {validation_result.get('warnings', [])}. "
                    "Please fix these issues and provide corrected BPMN XML."
                )
            }
            messages.append({"role": "assistant", "content": response})
            messages.append(validation_feedback)
            
            # Continue to next iteration
            continue
        else:
            # No BPMN XML found, return as-is
            return response
    
    # Max iterations reached
    return response + "\n\n[Note: Maximum validation iterations reached]"
