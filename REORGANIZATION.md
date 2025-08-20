# AgenticBobs - Codebase Reorganization

## Overview

The AgenticBobs codebase has been reorganized to follow industry best practices and the architecture outlined in `agentic_bobs.md`. This reorganization addresses several key issues and prepares the codebase for future development.

## New Structure

The codebase now follows a **src-layout** structure:

```
src/agentic_process_automation/
├── __init__.py                    # Main package
├── app/                          # 🎨 UI + orchestration layer
│   ├── __init__.py
│   ├── main.py                   # Main Streamlit application
│   ├── main2.py                  # Alternative implementation
│   └── editors.py                # BPMN/DMN editor integration
├── core/                         # 🧠 Core process automation logic
│   ├── __init__.py
│   ├── pir.py                    # Process Intermediate Representation
│   ├── scenario.py               # Simulation scenarios
│   ├── resources.py              # Resource management
│   ├── stochastic.py             # Random distributions
│   ├── semantics.py              # Process semantics
│   ├── sim.py                    # Core simulation
│   ├── adapters/                 # 🔌 Format adapters
│   │   ├── __init__.py
│   │   ├── bpmn_spiff.py         # BPMN via SpiffWorkflow
│   │   ├── bpmn_min.py           # Minimal BPMN parser
│   │   └── dmn_provider.py       # DMN decision engine
│   ├── sim/                      # 🎯 Simulation engine (from sim_dsl)
│   │   ├── __init__.py
│   │   ├── core.py               # Core simulation logic
│   │   ├── metrics.py            # Performance metrics
│   │   ├── resources.py          # Resource modeling
│   │   ├── simpy_adapter.py      # SimPy integration
│   │   └── ...
│   └── visualizers/              # 📊 Visualization components
├── qa/                           # ✅ Quality assurance
│   ├── __init__.py
│   └── conformance_pm4py.py      # Process conformance checking
├── ops/                          # 📈 Operations & monitoring
│   ├── __init__.py
│   ├── tracking.py               # Event tracking
│   ├── telemetry.py              # Observability (OpenTelemetry)
│   ├── storage.py                # Data persistence (DuckDB)
│   └── optimize_roster.py        # Resource optimization (OR-Tools)
└── cli/                          # 🖥️ Command-line tools
    ├── __init__.py
    ├── generate_xml.py           # Process generation
    ├── validate_bpmn.py          # BPMN validation
    ├── pipeline.py               # End-to-end pipeline
    └── ...
```

## Key Changes

### 1. **Resolved Package Structure Issues**
- ✅ **Fixed setuptools error**: Multiple top-level packages now properly organized
- ✅ **Src-layout**: Follows Python packaging best practices
- ✅ **Clean imports**: Proper `__init__.py` files with controlled exports

### 2. **Architecture Compliance** 
- ✅ **Matches documented design**: Follows structure from `agentic_bobs.md`
- ✅ **Separation of concerns**: Clear boundaries between UI, core logic, QA, and operations
- ✅ **Modular design**: Each component has specific responsibilities

### 3. **Dependency Management**
- ✅ **Optional dependencies**: Graceful fallbacks when optional packages missing
- ✅ **Grouped dependencies**: AI, process, optimization, monitoring, data, dev
- ✅ **Progressive enhancement**: Core works without optional features

### 4. **Improved Maintainability**
- ✅ **Clear entry points**: Defined CLI and app entry points
- ✅ **Consolidated logic**: Merged `sim_dsl` into `core/sim/`
- ✅ **Better organization**: Related functionality grouped together

## Migration Guide

### For Developers

**Old imports:**
```python
from core.pir import PIR, PIRBuilder
from core.adapters.bpmn import parse_bpmn
from marvin_scripts.generate_xml import generate_process_xml
```

**New imports:**
```python
from agentic_process_automation.core import PIR, PIRBuilder
from agentic_process_automation.core.adapters.bpmn_spiff import parse_bpmn
from agentic_process_automation.cli.generate_xml import generate_process_xml
```

### For Users

**Installation:**
```bash
# Basic installation
pip install -e .

# With all features
pip install -e ".[all]"

# Specific feature sets
pip install -e ".[ai,process,optimization]"
```

**Running the app:**
```bash
# Via package entry point
agenticbobs-app

# Or directly
streamlit run src/agentic_process_automation/app/main.py
```

## Benefits of Reorganization

### 🏗️ **Technical Benefits**
- **Package Discovery**: No more setuptools errors
- **Import Clarity**: Clear, hierarchical imports
- **Testing**: Better test organization and execution
- **Distribution**: Ready for PyPI packaging

### 🎯 **Architectural Benefits**
- **Scalability**: Easy to add new components
- **Maintainability**: Clear ownership of functionality
- **Modularity**: Components can be used independently
- **Documentation**: Structure self-documents the architecture

### 🚀 **Development Benefits**
- **Onboarding**: New developers can understand structure quickly
- **Feature Development**: Clear places to add new functionality
- **Debugging**: Easier to locate and fix issues
- **Deployment**: Ready for containerization and CI/CD

## Optional Dependencies

The package is designed with progressive enhancement:

| Feature Group | Packages | Functionality |
|---------------|----------|---------------|
| **Core** | pydantic, streamlit, simpy | Basic PIR, UI, simulation |
| **AI** | marvin | Agent-based process generation |
| **Process** | spiffworkflow | Industrial BPMN execution |
| **Optimization** | ortools | Resource assignment optimization |
| **Monitoring** | opentelemetry | Distributed tracing |
| **Data** | duckdb, pm4py | Analytics and conformance |

## Next Steps

1. **Update remaining tests** to use new import structure
2. **Update examples** and documentation
3. **Create integration tests** for the full pipeline
4. **Add CLI documentation** and help text
5. **Package for distribution** on PyPI

The reorganization provides a solid foundation for building the next generation of process automation tools! 🎉