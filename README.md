# Agentic Process Automation

An AI agent that works with process owners to formalize their processes and automate them using simulation, validation, and process modeling.

## 🏗️ Architecture

This project follows a clean, modular architecture designed for scalability and maintainability:

```
src/agentic_process_automation/
├── app/                    # 🎨 UI layer (Streamlit applications)
├── core/                   # 🧠 Core logic (PIR, simulation, adapters) 
├── qa/                     # ✅ Quality assurance (conformance checking)
├── ops/                    # 📈 Operations (monitoring, optimization)
└── cli/                    # 🖥️ Command-line tools
```

## 🚀 Quick Start

### Installation

```bash
# Basic installation (core functionality)
pip install -e .

# Full installation with all features
pip install -e ".[all]"

# Specific feature groups
pip install -e ".[ai,process,optimization]"
```

### Running the Application

```bash
# Using the entry point (once installed)
agenticbobs-app

# Or directly with Streamlit
PYTHONPATH=src streamlit run src/agentic_process_automation/app/main.py
```

### Development

```bash
# Run tests
PYTHONPATH=src python -m pytest tests/ -v

# Test the reorganized structure  
PYTHONPATH=src python test_new_structure.py
```

## 📦 Feature Groups

The package uses optional dependencies for progressive enhancement:

| Group | Features | Install |
|-------|----------|---------|
| **Core** | PIR, simulation, UI | *included* |
| **AI** | Agent-based generation | `[ai]` |
| **Process** | BPMN execution | `[process]` |
| **Optimization** | Resource optimization | `[optimization]` |
| **Monitoring** | Observability | `[monitoring]` |
| **Data** | Analytics, conformance | `[data]` |

## 🧪 Testing

```bash
# Run core tests (no external dependencies)
PYTHONPATH=src python -m pytest tests/test_pir.py tests/test_viz.py -v

# Test new structure
PYTHONPATH=src python test_new_structure.py

# Full test suite (requires optional dependencies)
PYTHONPATH=src python -m pytest tests/ -v
```

## 📖 Documentation

- **[REORGANIZATION.md](REORGANIZATION.md)** - Details about the codebase reorganization
- **[MARVIN_INTEGRATION.md](MARVIN_INTEGRATION.md)** - AI framework integration
- **[agentic_bobs.md](agentic_bobs.md)** - Original architecture specification

## 🏛️ Architecture Highlights

### Process Intermediate Representation (PIR)
Central abstraction for all process models:
```python
from agentic_process_automation.core import PIRBuilder

builder = PIRBuilder()
builder.add_node(id="start", kind="start", name="Begin")
builder.add_node(id="task", kind="task", name="Do Work")
builder.add_edge(src="start", dst="task")
pir = builder.build()
```

### Simulation Engine
SimPy-based process simulation:
```python
from agentic_process_automation.core import create_default_scenario
from agentic_process_automation.core.sim import run_simulation

scenario = create_default_scenario("test")
results = run_simulation(pir, scenario)
```

### Quality Assurance
Process conformance checking:
```python
from agentic_process_automation.qa import ConformanceChecker

checker = ConformanceChecker()
report = checker.check_conformance(event_log, process_model)
```

## 🎯 Key Components

- **PIR (Process IR)**: Universal process representation
- **Adapters**: BPMN, DMN, CMMN format support  
- **Simulation**: SimPy-based discrete event simulation
- **AI Integration**: Marvin-based agent framework
- **Validation**: Process model validation and conformance
- **Optimization**: OR-Tools resource assignment
- **Monitoring**: OpenTelemetry observability

## 🤝 Contributing

The reorganized codebase makes contribution easier:

1. **UI changes**: Edit files in `src/agentic_process_automation/app/`
2. **Core logic**: Modify `src/agentic_process_automation/core/`
3. **New adapters**: Add to `src/agentic_process_automation/core/adapters/`
4. **Monitoring**: Extend `src/agentic_process_automation/ops/`

## 📄 License

This project is licensed under the MIT License.

---

*Previously known as AgenticBobs - now evolved into a comprehensive process automation platform!* 🤖

