# Notebooks

This directory contains Jupyter notebooks organized by purpose.

## Directory Structure

### `analysis/`

Process analysis and visualization notebooks:

- `process_analysis_recovered.ipynb` - Main process analysis and visualization (recovered from corrupted file)
- `process_visuals.ipynb` - Process visualization and simulation charts

### `experiments/`

Experimental and research notebooks:

- `a_thing.ipynb` - Agent experimentation and workflow testing
- `process_mutations.ipynb` - Process mutation and modification experiments
- `try_egraphs.ipynb` - E-graphs research and testing

### `demos/`

Demonstration and tutorial notebooks:

- `agent_structure.ipynb` - Agent structure and architecture demos
- `show_process_validator_working.ipynb` - Process validation system demonstration

## Usage

To run notebooks:

```bash
# Configure environment first
uv run jupyter lab
```

Or use VS Code's built-in notebook support.

## Dependencies

All notebooks use the project's dependencies from `pyproject.toml`. Make sure to have the environment configured:

```bash
uv sync
```
