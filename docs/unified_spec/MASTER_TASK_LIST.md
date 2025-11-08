# Master Task List: Unified Spec for Human-AI Knowledge Work

This document outlines the high-level tasks required to implement the unified spec for human-AI knowledge work, as detailed in the project brief. It is a living document and will be updated as the project progresses.

## Phase 1: Language & Core Data Models (The Spec)

This phase focuses on defining the vocabulary and structure of the new specification.

- [x] **Task 1.1: Define Core Pydantic Models:**
    - [x] `Case`: The relational container for work state.
    - [x] `View`: The functional lens into the Case.
    - [x] `WorkUnit`: The executor-agnostic unit of work.
    - [x] `Combinator`: Functional operators like `map` and `fold`.
    - [x] `ExecutionBinding`: The policy linking a WorkUnit to an implementation.
    - [x] `WorkGraph`: The top-level container for a complete process specification.
    - [x] `WorkItem`: A specific, parameterized instance of a `WorkUnit`.

- [ ] **Task 1.2: Define Serialization Format:**
    - [ ] Decide on a primary serialization format (YAML or JSON).
    - [ ] Develop a JSON Schema from the Pydantic models for validation.

- [x] **Task 1.3: Create Example Specifications:**
    - [x] Write a complete `WorkGraph` spec in the chosen format for the "RFP Triage" example from the project brief.
    - [ ] Create a second, more complex example to test the expressiveness of the language.

## Phase 2: The Interpreter & Runtime

This phase focuses on building the engine that executes a `WorkGraph` specification.

- [x] **Task 2.1: Implement the `Case` State Manager:**
    - [x] Create a class to load, manage, and persist the state of a `Case` instance. For now, this will be an in-memory Pydantic object graph.

- [x] **Task 2.2: Develop the `View` Evaluation Engine:**
    - [x] Implement logic to resolve a `View` definition against a `Case` instance.
    - [x] Support for parameterized queries, `IN` clauses, and column aliases.

- [x] **Task 2.3: Build the Core Interpreter Loop:**
    - [x] Create a class that takes a `WorkGraph` and a `Case` as input.
    - [x] Implement the core logic:
        - [x] Evaluate `Done Conditions` for all active `Work Units`.
        - [x] Identify and schedule the next set of available `Work Units` as `WorkItem`s.
        - [x] Implement logic for `Combinators` (starting with `map`).

## Phase 3: Executors & Bindings

This phase focuses on connecting the abstract `Work Units` to concrete implementations.

- [ ] **Task 3.1: Implement the `ExecutionBinding` Dispatcher:**
    - [ ] Create a mechanism that resolves the `ExecutionBinding` for a given `WorkUnit` and routes it to the appropriate executor.

- [ ] **Task 3.2: Create a "Human" Executor:**
    - [ ] Build a simple executor that logs the `WorkUnit` and its input `Views` to a task list (e.g., a simple file or database table). This simulates a human picking up the work.

- [ ] **Task 3.3: Create an "Agent" Executor:**
    - [ ] Build an executor that uses the existing `ai.py` service.
    - [ ] The executor will format the input `Views` into a prompt for an LLM and execute the tool call defined by the `WorkUnit`.

## Phase 4: API & UI Integration

This phase focuses on exposing the new engine through the existing application infrastructure.

- [ ] **Task 4.1: Develop FastAPI Endpoints:**
    - [ ] `POST /workgraph`: Load and validate a new `WorkGraph` specification.
    - [ ] `POST /case`: Create a new `Case` instance from a `WorkGraph`.
    - [ ] `POST /case/{case_id}/tick`: Advance the state of a case by one interpreter cycle.
    - [ ] `GET /case/{case_id}`: Get the current state of a case.
    - [ ] `GET /case/{case_id}/tasks`: Get the list of pending human tasks.

- [ ] **Task 4.2: Frontend Visualization in 'thebobs':**
    - [ ] Create a new page to render a `WorkGraph` specification visually (based on the new visual grammar).
    - [ ] Display the current state of a `Case` instance.
    - [ ] Display a simple task list for the human executor.

## Phase 5: Refinement & Co-Design

This phase focuses on maturing the platform and preparing it for real-world use.

- [ ] **Task 5.1: Develop Visual Notation:**
    - [ ] Create a Figma/FigJam component library for the visual grammar described in the brief.

- [ ] **Task 5.2: Experimentation Framework:**
    - [ ] Build tools to easily A/B test different `ExecutionBindings` for the same `WorkGraph`.
    - [ ] Define and track key performance metrics (time to completion, quality, etc.).
