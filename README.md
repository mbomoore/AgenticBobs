# AgenticBobs

An AI-powered business process automation consultant that helps formalize, analyze, and optimize business processes using BPMN/DMN modeling and simulation.

## Project Structure

```text
AgenticBobs/
├── src/                     # Source code
│   └── agentic_process_automation/
├── tests/                   # Test suite
├── notebooks/               # Jupyter notebooks
│   ├── analysis/           # Process analysis and visualization
│   ├── experiments/        # Research and experimentation
│   └── demos/              # Demonstrations and tutorials
├── docs/                    # Documentation
├── data/                    # Sample data and assets
├── examples/               # Example scripts and workflows
├── scripts/                # Utility scripts
├── backend/                # Backend API server
└── thebobs/                # Frontend application
```

## Quick Start

### Installation

```bash
# Install dependencies
uv sync

# Run tests
uv run python -m pytest -q
```

### Launch The Bobs 2.0

```bash
# Start both frontend and backend servers
./start.sh
```

This launches:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>

### Run Streamlit App (Alternative)

```bash
# Launch main Streamlit application
python main.py
```

## Development

### Local Component Sanity Check

If the bpmn.io component has trouble loading, use the built-in minimal component under the "Sanity Check" tab in the app. It uses no external JS and simply echoes a timestamp and counter when you click its button. This helps confirm the Streamlit custom component pipeline is working locally.

### Notebooks

Explore the analysis and experimentation notebooks:

```bash
uv run jupyter lab
```

See `notebooks/README.md` for details on available notebooks.

## Architecture

See `docs/ARCHITECTURE.md` for detailed system architecture and component overview.

