# A Unified Spec for Human-AI Knowledge Work

This project is building a unified specification and runtime where designing a business process and designing an agentic system are the same activity. It treats AI agents not as a separate, alien species, but as coworkers in the same process maps we already use to think about people.

The core idea is to move away from the traditional separation of:
- **“Agentic systems design”** → agents, tools, planners, swarms.
- **“Process mapping”** → BPMN, swimlanes, SOPs for how humans work.

As soon as you touch real-world knowledge work—underwriting, proposal creation, strategic analysis—these two worlds blur. The process isn’t fully known until you walk through it with the humans, and the "best" process is often co-designed as you introduce new tooling and AI.

This project provides a single spec where mapping what the humans do and designing what the agents will do are **the same artifact**.

## The Core Primitives

The spec is built around a few neutral primitives that don’t care who executes them:

1.  **Case** – The shared, relational world in which the work happens.
2.  **Views** – Functionally-inspired “lenses” or queries into the Case.
3.  **Work Units** – Goal-directed, executor-agnostic tasks that transform the Case.
4.  **Combinators** – Functional patterns like `map`, `fold`, and `filter` over sets of Work Units.
5.  **Execution Bindings** – The policy layer where you finally decide if a task is for a human, an AI, or a hybrid.

This structure lets you diagram a team's workflow and later—or in parallel—attach bindings that say: “*This step is an LLM agent*,” “*this one is a human*,” or “*this is a swarm of agents with human adjudication*.”

Change the bindings; don’t change the work spec.

## Project Status

The project is currently in **Phase 2: The Interpreter & Runtime**. The core data models (`Case`, `View`, `WorkUnit`, etc.) are defined as Pydantic models, and a foundational version of the interpreter has been built. This interpreter can read a `WorkGraph` specification and determine the next set of "ready" tasks based on their preconditions.

For a detailed roadmap, see `docs/unified_spec/MASTER_TASK_LIST.md`.

## Quick Start

### Installation

```bash
# Install dependencies
uv sync

# Run tests
uv run python -m pytest -q
```

### Launch The Bobs 2.0

The primary user interface for this project is the "Bobs 2.0" Vue.js application.

```bash
# Start both frontend and backend servers
./start.sh
```

This launches:
- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>

## Development

The core logic for the new unified spec is being developed in `src/agentic_process_automation/core/unified_spec/`.

Tests for this new functionality are located in `tests/core/unified_spec/`. To run only these tests:
```bash
uv run python -m pytest tests/core/unified_spec/
```

### Architecture

For a detailed system architecture and component overview, see `docs/ARCHITECTURE.md`.
