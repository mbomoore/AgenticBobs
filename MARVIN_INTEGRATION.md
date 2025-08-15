# AgenticBobs: Marvin Integration

This document describes the integration of the Marvin agent framework to replace the custom tool calling system.

## What Changed

### Dependencies
- Added `marvin>=3.1.0` to pyproject.toml
- Marvin provides a robust agent framework built on pydantic-ai

### Agent Framework (core/ai.py)
- **Replaced custom tool system** with Marvin's `@marvin.fn` decorator
- **Enhanced agent_chat()** to use Marvin agents with automatic fallback
- **Maintained backwards compatibility** for existing tests and API

### Key Improvements

1. **Professional Framework**: Uses established Marvin patterns instead of custom implementation
2. **Robust Tool Calling**: Marvin provides battle-tested tool calling and agent capabilities  
3. **Flexible Backend**: Supports multiple LLM providers (OpenAI, local models via OpenAI-compatible API)
4. **Graceful Fallback**: Falls back to original Ollama implementation if Marvin fails

## Configuration for Production

### Using OpenAI (Default)
```bash
export OPENAI_API_KEY="your-api-key"
```

### Using Local Ollama
```bash
export OPENAI_API_KEY="dummy-key"
export OPENAI_BASE_URL="http://localhost:11434/v1"
```

### Using Other Providers
Marvin supports many providers through pydantic-ai:
- Anthropic Claude
- Google Gemini
- Azure OpenAI
- Cohere
- And more...

## Technical Details

The implementation maintains the same external API while using Marvin internally:

- `validate_bpmn()` - Direct validation function (no LLM needed)
- `marvin_validate_bpmn()` - Marvin-compatible tool for agent workflows
- `agent_chat()` - Enhanced with Marvin agent support + fallback
- Legacy compatibility layer preserves existing test API

## Benefits

✅ **Industry Standard**: Uses established Marvin framework  
✅ **Robust Tool Calling**: Professional agent capabilities  
✅ **Multiple Providers**: Flexible LLM backend support  
✅ **Backwards Compatible**: All existing tests pass  
✅ **Graceful Degradation**: Falls back to original implementation  

This transformation elevates AgenticBobs from a custom implementation to a professional-grade agent system using industry-standard tools.