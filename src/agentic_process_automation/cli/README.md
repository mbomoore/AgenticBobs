Marvin Scripts
==============

Small, mostly independent scripts that mirror notebook flows in `agent_structure.ipynb`.

Requirements
------------
- uv-based environment (see pyproject.toml) 
- pydantic-ai, marvin, SpiffWorkflow installed via uv
- An OpenAI-compatible endpoint (defaults to http://localhost:11434/v1 with model `qwen3:4b`)

Environment variables (optional):
- LLM_BASE_URL (default: http://localhost:11434/v1)
- LLM_MODEL_NAME (default: qwen3:4b)
- LLM_API_KEY (default: empty)

Scripts
-------
- marvin_scripts.detect_type: Detect BPMN/DMN/CMMN from a description
- marvin_scripts.generate_xml: Generate process XML using Bob_2
- marvin_scripts.validate_bpmn: Validate BPMN via SpiffWorkflow
- marvin_scripts.pipeline: End-to-end detect -> generate -> validate

Examples
--------
Detect type:
  uv run python -m marvin_scripts.detect_type --description "We take an order, fulfill, and ship it."

Generate XML (assumes BPMN):
  uv run python -m marvin_scripts.generate_xml --description "We take an order, fulfill, and ship it." --type BPMN

Validate BPMN:
  uv run python -m marvin_scripts.validate_bpmn < model.bpmn

Pipeline (detect + generate + validate):
  uv run python -m marvin_scripts.pipeline --description "We take an order, fulfill, and ship it."
