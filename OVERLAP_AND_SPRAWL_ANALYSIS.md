# AgenticBobs - Overlap and Sprawl Analysis

*Analysis Date: August 22, 2025*

## 🚨 Major Areas of Overlap and Sprawl

### 1. **DUPLICATE MODULE STRUCTURE** - 🔴 Critical Sprawl

#### Problem: Two Identical `marvin_scripts` Directories
- **Location 1**: `/marvin_scripts/` (project root)
- **Location 2**: `/src/agentic_process_automation/cli/` 
- **Files Duplicated**: 
  - `generate_xml.py` (literally identical implementations)
  - `common.py` 
  - `detect_type.py`
  - `generate_refinement_questions.py`

**Evidence**: Both contain identical `ProcessGenerationConfig` classes and `generate_process_xml` functions.

**Impact**: 
- Developer confusion about which to import
- Potential for divergence and bugs
- Import path inconsistencies across the codebase

---

### 2. **MULTIPLE MAIN ENTRY POINTS** - 🔴 Critical Sprawl

#### Problem: Too Many Ways to Start the Application
- **Root main.py**: Streamlit launcher calling app/main.py
- **backend/main.py**: FastAPI application 
- **backend/dev_server.py**: Development server wrapper
- **src/agentic_process_automation/app/main.py**: Core Streamlit app
- **start.sh**: Shell script orchestrator

**Evidence**: 
```python
# /main.py - launches streamlit
# /backend/main.py - FastAPI server
# /backend/dev_server.py - uvicorn wrapper
# /src/.../app/main.py - actual streamlit app
```

**Impact**:
- Unclear which is the "real" entry point
- Deployment complexity
- Documentation confusion

---

### 3. **VALIDATION LOGIC SCATTERED** - 🟡 Medium Sprawl

#### Problem: Multiple Validation Implementations
- **Location 1**: `core/pir.py` - PIR structure validation
- **Location 2**: `core/validators/validators.py` - Generic validation
- **Location 3**: `core/bpmn_validator.py` - BPMN-specific validation
- **Location 4**: `core/dmn_validator.py` - DMN-specific validation  
- **Location 5**: `core/ai.py` - AI-integrated validation functions
- **Location 6**: `backend/main.py` - API validation endpoint

**Evidence**: 
- `validate()` function in pir.py
- `validate_bpmn_string()` in bpmn_validator.py
- `validate_bpmn()` in ai.py
- `marvin_validate_bpmn()` also in ai.py
- `/api/validate-bpmn` endpoint

**Impact**: 
- Hard to know which validator to use when
- Inconsistent error message formats
- Duplication of validation logic

---

### 4. **AI INTEGRATION COMPLEXITY** - 🟡 Medium Sprawl

#### Problem: Multiple AI Integration Patterns
- **Ollama Direct**: `core/ai.py` with httpx client
- **Marvin Agents**: Also in `core/ai.py` 
- **Legacy Tools**: Compatibility layer in `core/ai.py`
- **Backend Integration**: `backend/main.py` using marvin_scripts
- **Streamlit Integration**: `app/main.py` using core/ai

**Evidence**: Multiple ways to call AI:
```python
# Direct Ollama
ai_chat(messages)

# Marvin Agent  
agent_chat(messages)

# Backend pipeline
generate_process_xml(config)
```

**Impact**:
- Code paths hard to follow
- Testing complexity
- Performance inconsistencies

---

### 5. **BPMN PARSING REDUNDANCY** - 🟡 Medium Sprawl

#### Problem: Multiple BPMN Parsers with Fallback Chains
- **Primary**: `core/adapters/bpmn.py` - SpiffWorkflow preferred
- **Fallback**: `core/adapters/bpmn_min.py` - Minimal parser
- **Layout**: `backend/bpmn_layout.py` - Custom XML parsing for layout
- **App Fallback**: `app/main.py` - Import fallback logic

**Evidence**:
```python
# Multiple parse_bpmn implementations
def parse_bpmn(xml_bytes: bytes) -> PIR:  # in bpmn.py
def from_bpmn_xml(xml_bytes: bytes):      # in bpmn_min.py  
def parse_bpmn_structure(self, bpmn_xml: str): # in layout.py
```

**Impact**:
- Unclear which parser is used when
- Different behavior in different contexts
- Testing complexity

---

### 6. **TEST FILES AT ROOT LEVEL** - 🟡 Medium Sprawl

#### Problem: Test Files Mixed with Source Code
- **Root Level Tests**: 
  - `test_advanced_layout.py`
  - `test_bob2_consistency.py` 
  - `test_bob2_debug.py`
  - `test_bobs_flow.py`
  - And 7 more...
- **Proper Tests**: `/tests/` directory with organized test suite

**Impact**:
- Confusion about which tests to run
- Mixed concerns at root level
- Harder to maintain test organization

---

### 7. **IMPORT PATH CONFUSION** - 🟡 Medium Sprawl

#### Problem: Multiple Ways to Import Same Functionality
```python
# Different ways to import the same function:
from marvin_scripts.generate_xml import generate_process_xml
from agentic_process_automation.cli.generate_xml import generate_process_xml

# Multiple validation imports:
from core.pir import validate  
from ..core.pir import validate
from ...core.pir import validate
```

**Impact**:
- IDE confusion and autocomplete issues
- Import errors in different contexts
- Refactoring difficulty

---

### 8. **CONFIGURATION SPRAWL** - 🟡 Medium Sprawl

#### Problem: Configuration Settings Scattered
- **AI Models**: Hardcoded in multiple files
- **URLs**: Different defaults in different modules
- **Paths**: Relative path assumptions everywhere
- **Environment**: No central config management

**Evidence**:
```python
DEFAULT_MODEL = "gpt-oss:20b"     # in core/ai.py
model_name="qwen3:8b"             # in cli/generate_xml.py  
"http://localhost:11434"          # in core/ai.py
"http://localhost:8000"           # in frontend stores
```

---

## 🎯 **Priority Consolidation Recommendations**

### **IMMEDIATE (High Impact, Easy Fix)**

1. **Merge Duplicate `marvin_scripts`** 
   - Choose `/src/agentic_process_automation/cli/` as canonical location
   - Delete `/marvin_scripts/` 
   - Update all imports to use canonical path

2. **Consolidate Test Files**
   - Move all `test_*.py` from root to `/tests/`
   - Update test discovery configuration

3. **Centralize Configuration**
   - Create `config.py` with all defaults
   - Remove hardcoded URLs/models from individual files

### **MEDIUM TERM (Moderate Impact)**

4. **Unify Validation Logic**
   - Create single `ValidationService` class
   - Consolidate all validation functions 
   - Standardize error message format

5. **Simplify Entry Points**
   - Choose FastAPI as primary backend
   - Make Streamlit app a frontend alternative  
   - Document clear deployment paths

6. **Standardize BPMN Parsing**
   - Single parse_bpmn function with clear fallback strategy
   - Document when each parser is appropriate

### **LONG TERM (Architectural Changes)**

7. **AI Integration Refactor**
   - Single AI service interface
   - Clear separation of Ollama vs Marvin capabilities
   - Unified configuration and error handling

8. **Import Path Cleanup**
   - Establish clear import conventions
   - Add proper __init__.py exports
   - Document import patterns

---

## 📊 **Sprawl Impact Assessment**

| Area | Severity | Developer Impact | User Impact | Effort to Fix |
|------|----------|------------------|-------------|---------------|
| Duplicate Modules | 🔴 High | Very High | Medium | Low |
| Multiple Main Files | 🔴 High | High | High | Medium |
| Validation Scatter | 🟡 Medium | Medium | Low | Medium |
| AI Integration | 🟡 Medium | High | Low | High |
| BPMN Parsing | 🟡 Medium | Medium | Low | Medium |
| Root Test Files | 🟡 Medium | Low | None | Low |
| Import Confusion | 🟡 Medium | High | None | Medium |
| Config Sprawl | 🟡 Medium | Medium | Low | Low |

---

## 🚀 **Recommended Cleanup Sequence**

1. **Week 1**: Merge duplicate marvin_scripts, move test files
2. **Week 2**: Centralize configuration, standardize imports  
3. **Week 3**: Consolidate validation logic
4. **Week 4**: Simplify entry points and deployment
5. **Week 5**: Unify BPMN parsing strategy
6. **Week 6**: Refactor AI integration architecture

**Estimated Total Effort**: 4-6 weeks of focused refactoring

The biggest immediate wins come from eliminating the duplicate module structure and consolidating the scattered test files. These changes will immediately improve developer experience and reduce confusion.

---

## � **RAPID CONSOLIDATION PLAN** (Execute in 30 minutes)

> **This is a new library** - no need for weeks-long migration. Fix the sprawl immediately and establish clean architecture.

### **STEP 1: Immediate Cleanup (5 minutes)**

```bash
# 1. Delete duplicate directory
rm -rf marvin_scripts/

# 2. Move scattered tests
mv test_*.py tests/

# 3. Update imports in backend/main.py (ONE FILE to change)
sed -i '' 's/from marvin_scripts\./from src.agentic_process_automation.cli./g' backend/main.py

# 4. Test everything still works
uv run python -m pytest tests/ -q
./start.sh
```

### **STEP 2: Create Event-Driven Architecture (15 minutes)**

Create the new core architecture:

```python
# src/agentic_process_automation/core/events.py
"""Event-driven architecture for AgenticBobs."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

class EventType(Enum):
    PROCESS_GENERATE_REQUEST = "process.generate.request"
    PROCESS_GENERATE_RESPONSE = "process.generate.response"
    PROCESS_VALIDATE_REQUEST = "process.validate.request"
    PROCESS_VALIDATE_RESPONSE = "process.validate.response"
    PROCESS_REFINE_REQUEST = "process.refine.request"
    PROCESS_REFINE_RESPONSE = "process.refine.response"
    UI_STATE_CHANGE = "ui.state.change"
    ERROR_OCCURRED = "error.occurred"

@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    source: str
    correlation_id: Optional[str] = None
    timestamp: Optional[float] = None

class EventBus:
    """Central event bus for all AgenticBobs communication."""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to events of a specific type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        await self._queue.put(event)
    
    async def start_processing(self):
        """Start the event processing loop."""
        while True:
            event = await self._queue.get()
            await self._handle_event(event)
    
    async def _handle_event(self, event: Event):
        """Handle a single event by calling all subscribers."""
        if event.type in self._subscribers:
            for handler in self._subscribers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    error_event = Event(
                        type=EventType.ERROR_OCCURRED,
                        data={"error": str(e), "original_event": event},
                        source="event_bus"
                    )
                    # Don't await to prevent infinite loops
                    asyncio.create_task(self.publish(error_event))

# Global event bus instance
event_bus = EventBus()
```

```python
# src/agentic_process_automation/core/services.py  
"""Core services with dependency injection."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from .events import Event, EventType, event_bus
from .pir import PIR, validate

class ProcessService:
    """Core business logic for process operations."""
    
    def __init__(self, ai_service, validator_service):
        self.ai_service = ai_service
        self.validator_service = validator_service
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        event_bus.subscribe(EventType.PROCESS_GENERATE_REQUEST, self._handle_generate)
        event_bus.subscribe(EventType.PROCESS_VALIDATE_REQUEST, self._handle_validate)
        event_bus.subscribe(EventType.PROCESS_REFINE_REQUEST, self._handle_refine)
    
    async def _handle_generate(self, event: Event):
        """Handle process generation requests."""
        try:
            xml = await self.ai_service.generate_process_xml(
                event.data["description"], 
                event.data.get("process_type", "BPMN")
            )
            
            response = Event(
                type=EventType.PROCESS_GENERATE_RESPONSE,
                data={"xml": xml, "success": True},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(response)
            
        except Exception as e:
            error_response = Event(
                type=EventType.PROCESS_GENERATE_RESPONSE,
                data={"error": str(e), "success": False},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(error_response)
    
    async def _handle_validate(self, event: Event):
        """Handle validation requests."""
        result = self.validator_service.validate_bpmn_xml(event.data["xml"])
        
        response = Event(
            type=EventType.PROCESS_VALIDATE_RESPONSE,
            data={"validation_result": result},
            source="process_service",
            correlation_id=event.correlation_id
        )
        await event_bus.publish(response)
    
    async def _handle_refine(self, event: Event):
        """Handle process refinement requests."""
        try:
            xml = await self.ai_service.refine_process(
                event.data["current_xml"],
                event.data["feedback"]
            )
            
            response = Event(
                type=EventType.PROCESS_REFINE_RESPONSE,
                data={"xml": xml, "success": True},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(response)
            
        except Exception as e:
            error_response = Event(
                type=EventType.PROCESS_REFINE_RESPONSE,
                data={"error": str(e), "success": False},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(error_response)

class AIService(ABC):
    """Abstract interface for AI services."""
    
    @abstractmethod
    async def generate_process_xml(self, description: str, process_type: str) -> str:
        pass
    
    @abstractmethod
    async def refine_process(self, current_xml: str, feedback: str) -> str:
        pass

class ValidatorService:
    """Unified validation service."""
    
    def validate_bpmn_xml(self, xml: str) -> Dict[str, Any]:
        try:
            from .adapters.bpmn import parse_bpmn
            pir = parse_bpmn(xml.encode('utf-8'))
            result = validate(pir)
            return {
                "is_valid": len(result["errors"]) == 0,
                "errors": result["errors"],
                "warnings": result["warnings"]
            }
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Parse error: {str(e)}"],
                "warnings": []
            }
```

### **STEP 3: Frontend Abstraction (10 minutes)**

```python
# src/agentic_process_automation/frontends/base.py
"""Abstract frontend interface with dependency injection."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..core.events import Event, EventType, event_bus
import uuid

class Frontend(ABC):
    """Abstract base class for all AgenticBobs frontends."""
    
    def __init__(self, name: str):
        self.name = name
        self._session_data: Dict[str, Any] = {}
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Override in subclasses to handle specific events."""
        pass
    
    async def generate_process(self, description: str, process_type: str = "BPMN") -> str:
        """Request process generation and wait for response."""
        correlation_id = str(uuid.uuid4())
        
        # Set up response handler
        response_received = False
        result = {}
        
        def handle_response(event: Event):
            nonlocal response_received, result
            if event.correlation_id == correlation_id:
                result.update(event.data)
                response_received = True
        
        event_bus.subscribe(EventType.PROCESS_GENERATE_RESPONSE, handle_response)
        
        # Send request
        request = Event(
            type=EventType.PROCESS_GENERATE_REQUEST,
            data={"description": description, "process_type": process_type},
            source=self.name,
            correlation_id=correlation_id
        )
        await event_bus.publish(request)
        
        # Wait for response (simplified - in real implementation use proper async patterns)
        import asyncio
        timeout = 30
        elapsed = 0
        while not response_received and elapsed < timeout:
            await asyncio.sleep(0.1)
            elapsed += 0.1
        
        if not response_received:
            raise TimeoutError("Process generation timed out")
        
        if not result.get("success"):
            raise Exception(result.get("error", "Unknown error"))
        
        return result["xml"]
    
    @abstractmethod
    async def start(self):
        """Start the frontend interface."""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the frontend interface."""
        pass

# Frontend implementations
class StreamlitFrontend(Frontend):
    """Streamlit-based frontend."""
    
    def __init__(self):
        super().__init__("streamlit")
    
    async def start(self):
        # Import and start existing Streamlit app
        import subprocess
        subprocess.run([
            "streamlit", "run", 
            "src/agentic_process_automation/app/main.py"
        ])

class FastAPIFrontend(Frontend):
    """FastAPI-based frontend."""
    
    def __init__(self):
        super().__init__("fastapi")
        self.app = None
    
    async def start(self):
        # Import and start existing FastAPI app
        from backend.main import app
        self.app = app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)

class VueFrontend(Frontend):
    """Vue.js-based frontend."""
    
    def __init__(self):
        super().__init__("vue")
    
    async def start(self):
        # Start Vue development server
        import subprocess
        subprocess.run(["npm", "run", "dev"], cwd="thebobs")

# Frontend factory
class FrontendFactory:
    @staticmethod
    def create(frontend_type: str) -> Frontend:
        if frontend_type == "streamlit":
            return StreamlitFrontend()
        elif frontend_type == "fastapi":
            return FastAPIFrontend()
        elif frontend_type == "vue":
            return VueFrontend()
        else:
            raise ValueError(f"Unknown frontend type: {frontend_type}")
```

```python
# src/agentic_process_automation/main.py
"""Main application runner with dependency injection."""
import asyncio
from typing import List, Optional
from .core.events import event_bus
from .core.services import ProcessService, ValidatorService
from .frontends.base import FrontendFactory

class AgenticBobsApp:
    """Main application orchestrator."""
    
    def __init__(self):
        self.services = {}
        self.frontends: List = []
        self._setup_services()
    
    def _setup_services(self):
        """Initialize core services with dependency injection."""
        from .core.ai import MarvinAgentService  # Your existing AI service
        
        # Create services
        ai_service = MarvinAgentService()
        validator_service = ValidatorService()
        
        # Register services
        self.services['ai'] = ai_service
        self.services['validator'] = validator_service
        self.services['process'] = ProcessService(ai_service, validator_service)
    
    def add_frontend(self, frontend_type: str):
        """Add a frontend to the application."""
        frontend = FrontendFactory.create(frontend_type)
        self.frontends.append(frontend)
    
    async def start(self, frontends: Optional[List[str]] = None):
        """Start the application with specified frontends."""
        if frontends is None:
            frontends = ["fastapi"]  # Default to API only
        
        # Add requested frontends
        for frontend_type in frontends:
            self.add_frontend(frontend_type)
        
        # Start event processing
        event_task = asyncio.create_task(event_bus.start_processing())
        
        # Start frontends
        frontend_tasks = []
        for frontend in self.frontends:
            task = asyncio.create_task(frontend.start())
            frontend_tasks.append(task)
        
        # Wait for all tasks
        await asyncio.gather(event_task, *frontend_tasks)

# Simple CLI
def main():
    import sys
    
    app = AgenticBobsApp()
    
    if len(sys.argv) == 1:
        # Default: run FastAPI + Vue
        frontends = ["fastapi", "vue"]
    else:
        # Allow specifying frontends
        frontends = sys.argv[1:]
    
    print(f"🤖 Starting AgenticBobs with frontends: {frontends}")
    asyncio.run(app.start(frontends))

if __name__ == "__main__":
    main()
```

### **DONE! (30 minutes total)**

**Usage**:
```bash
# API only
python -m agentic_process_automation.main fastapi

# Full web app  
python -m agentic_process_automation.main fastapi vue

# Streamlit alternative
python -m agentic_process_automation.main streamlit

# All three frontends
python -m agentic_process_automation.main fastapi vue streamlit
```

**Benefits of New Architecture**:
- ✅ **Single source of truth**: All business logic in `ProcessService`
- ✅ **Loose coupling**: Frontends communicate only via events
- ✅ **Easy testing**: Mock the event bus, test services independently  
- ✅ **Easy extension**: Add new frontends by implementing `Frontend` base class
- ✅ **Dependency injection**: Services are injected, easy to swap implementations
- ✅ **Event-driven**: Perfect for async operations and multiple UIs
- ✅ **No sprawl**: Clear separation of concerns

The old multiple main files become thin frontend wrappers, all real logic moves to the event-driven core.

---

## �📋 **LEGACY DETAILED CONSOLIDATION PLAN** (For Reference Only)

### **PHASE 1: IMMEDIATE CLEANUP (Week 1)**

#### Task 1.1: Eliminate Duplicate `marvin_scripts` Directory

**Goal**: Remove duplication and establish canonical import paths

**Steps**:
1. **Verify File Differences**:
   ```bash
   # Compare the two directories to confirm they're identical
   diff -r marvin_scripts/ src/agentic_process_automation/cli/
   ```

2. **Update All Imports**:
   ```bash
   # Find all files importing from marvin_scripts
   grep -r "from marvin_scripts" . --include="*.py"
   grep -r "import marvin_scripts" . --include="*.py"
   ```

3. **Replace Imports** in these files:
   - `backend/main.py`
   - Any other files found in step 2
   
   **Replace**:
   ```python
   from marvin_scripts.common import build_model
   from marvin_scripts.detect_type import bob_1
   from marvin_scripts.generate_xml import generate_process_xml, ProcessGenerationConfig
   from marvin_scripts.generate_refinement_questions import generate_refinement_questions, RefinementQuestionsConfig
   ```
   
   **With**:
   ```python
   from src.agentic_process_automation.cli.common import build_model
   from src.agentic_process_automation.cli.detect_type import bob_1
   from src.agentic_process_automation.cli.generate_xml import generate_process_xml, ProcessGenerationConfig
   from src.agentic_process_automation.cli.generate_refinement_questions import generate_refinement_questions, RefinementQuestionsConfig
   ```

4. **Update pyproject.toml** entry points if needed:
   ```bash
   # Check for any entry points referencing marvin_scripts
   grep -n "marvin_scripts" pyproject.toml
   ```

5. **Delete the Duplicate Directory**:
   ```bash
   rm -rf marvin_scripts/
   ```

6. **Test Everything Still Works**:
   ```bash
   uv run python -m pytest tests/ -v
   ./start.sh  # Test both frontend and backend start
   ```

#### Task 1.2: Consolidate Test Files

**Goal**: Move all tests to `/tests/` directory for organization

**Steps**:
1. **Move Test Files**:
   ```bash
   mv test_*.py tests/
   ```

2. **Update Test Discovery** in `pytest.ini`:
   ```ini
   [tool:pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   ```

3. **Fix Any Import Issues** in moved tests:
   ```bash
   # Run tests to identify import problems
   uv run python -m pytest tests/ -v
   ```

4. **Update Documentation** references to test files in README.md and docs/

#### Task 1.3: Create Central Configuration

**Goal**: Eliminate hardcoded values scattered throughout codebase

**Steps**:
1. **Create** `src/agentic_process_automation/config.py`:
   ```python
   """Central configuration for AgenticBobs application."""
   import os
   from typing import Optional
   
   class Config:
       # AI Models
       DEFAULT_SMALL_MODEL = "qwen3:8b"
       DEFAULT_LARGE_MODEL = "gpt-oss:20b"
       DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
       
       # API Endpoints
       DEFAULT_OLLAMA_URL = "http://localhost:11434"
       DEFAULT_API_URL = "http://localhost:8000"
       FRONTEND_URL = "http://localhost:5173"
       
       # Timeouts
       OLLAMA_TIMEOUT = 120.0
       API_TIMEOUT = 30.0
       
       # Environment overrides
       OLLAMA_URL = os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL)
       API_URL = os.getenv("API_URL", DEFAULT_API_URL)
       SMALL_MODEL = os.getenv("SMALL_MODEL", DEFAULT_SMALL_MODEL)
       LARGE_MODEL = os.getenv("LARGE_MODEL", DEFAULT_LARGE_MODEL)
   
   config = Config()
   ```

2. **Update Files to Use Config**:
   - `src/agentic_process_automation/core/ai.py`
   - `src/agentic_process_automation/cli/generate_xml.py`
   - `backend/main.py`
   - `thebobs/src/stores/chat.ts` (for API_URL)

3. **Replace Hardcoded Values**:
   ```python
   # OLD:
   DEFAULT_OLLAMA_URL = "http://localhost:11434"
   DEFAULT_MODEL = "gpt-oss:20b"
   
   # NEW:
   from ..config import config
   DEFAULT_OLLAMA_URL = config.OLLAMA_URL
   DEFAULT_MODEL = config.DEFAULT_OLLAMA_MODEL
   ```

**Validation**: Run full test suite and start application to ensure config works.

### **PHASE 2: STRUCTURAL CONSOLIDATION (Weeks 2-3)**

#### Task 2.1: Unify Validation Logic

**Goal**: Single validation interface with consistent error handling

**Steps**:
1. **Create** `src/agentic_process_automation/core/validation.py`:
   ```python
   """Unified validation service for all process types."""
   from typing import Dict, List, Union, Any
   from dataclasses import dataclass
   from .pir import PIR, validate as pir_validate
   
   @dataclass
   class ValidationResult:
       is_valid: bool
       errors: List[str]
       warnings: List[str]
       validation_type: str
       
   class ValidationService:
       """Central validation service for all process types."""
       
       def validate_pir(self, pir: PIR) -> ValidationResult:
           """Validate PIR structure."""
           result = pir_validate(pir)
           return ValidationResult(
               is_valid=len(result["errors"]) == 0,
               errors=result["errors"],
               warnings=result["warnings"],
               validation_type="PIR"
           )
       
       def validate_bpmn_xml(self, bpmn_xml: str) -> ValidationResult:
           """Validate BPMN XML and return unified result."""
           try:
               from .adapters.bpmn import parse_bpmn
               pir = parse_bpmn(bpmn_xml.encode('utf-8'))
               return self.validate_pir(pir)
           except Exception as e:
               return ValidationResult(
                   is_valid=False,
                   errors=[f"BPMN parse error: {str(e)}"],
                   warnings=[],
                   validation_type="BPMN"
               )
       
       def validate_dmn_xml(self, dmn_xml: str) -> ValidationResult:
           """Validate DMN XML."""
           # Implement DMN validation
           pass
   
   # Global instance
   validator = ValidationService()
   ```

2. **Update All Validation Callers**:
   - Replace calls to various validate functions with `validator.validate_bpmn_xml()`
   - Update `backend/main.py` validation endpoint
   - Update `core/ai.py` validation functions

3. **Deprecate Old Validation Functions**:
   - Add deprecation warnings to old functions
   - Update documentation to point to new service

#### Task 2.2: Simplify Entry Points

**Goal**: Clear primary/secondary application entry strategy

**Steps**:
1. **Establish Primary Entry Points**:
   - **Backend**: `backend/main.py` (FastAPI)
   - **Frontend**: `thebobs/` (Vue.js)
   - **Development**: `start.sh` (orchestrator)
   - **Alternative UI**: `src/agentic_process_automation/app/main.py` (Streamlit)

2. **Update Root `main.py`**:
   ```python
   #!/usr/bin/env python3
   """
   AgenticBobs Application Launcher
   
   Primary interfaces:
   - Web Application: ./start.sh (recommended)
   - Alternative UI: python main.py (Streamlit)
   - API Only: python backend/main.py
   """
   import sys
   import subprocess
   from pathlib import Path
   
   def main():
       print("🤖 AgenticBobs - AI Process Automation")
       print("\nAvailable interfaces:")
       print("1. Full Web Application (recommended): ./start.sh")
       print("2. Streamlit UI (current)")
       print("3. API Server only: python backend/main.py")
       print()
       
       # Launch Streamlit as alternative interface
       streamlit_app = Path("src/agentic_process_automation/app/main.py")
       subprocess.run([sys.executable, "-m", "streamlit", "run", str(streamlit_app)])
   
   if __name__ == "__main__":
       main()
   ```

3. **Consolidate `backend/dev_server.py`** into `backend/main.py`:
   ```python
   # Add to bottom of backend/main.py
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(
           "main:app",
           host="0.0.0.0", 
           port=8000,
           reload=True,
           log_level="info"
       )
   ```

4. **Delete `backend/dev_server.py`** and update `start.sh`:
   ```bash
   # Change in start.sh:
   # OLD: uv run python dev_server.py &
   # NEW: uv run python main.py &
   ```

### **PHASE 3: ARCHITECTURAL CONSOLIDATION (Weeks 4-5)**

#### Task 3.1: Standardize BPMN Parsing

**Goal**: Single, predictable BPMN parsing interface

**Steps**:
1. **Create** `src/agentic_process_automation/core/adapters/parser.py`:
   ```python
   """Unified BPMN parsing interface with clear fallback strategy."""
   from typing import Optional
   from ..pir import PIR
   from .bpmn import parse_bpmn as spiff_parse
   from .bpmn_min import from_bpmn_xml as minimal_parse
   
   class BPMNParsingStrategy:
       SPIFF_PREFERRED = "spiff"
       MINIMAL_ONLY = "minimal"
       SPIFF_WITH_FALLBACK = "spiff_fallback"
   
   def parse_bpmn_xml(
       xml_content: str, 
       strategy: str = BPMNParsingStrategy.SPIFF_WITH_FALLBACK
   ) -> PIR:
       """Single entry point for BPMN parsing with explicit strategy."""
       xml_bytes = xml_content.encode('utf-8')
       
       if strategy == BPMNParsingStrategy.MINIMAL_ONLY:
           return minimal_parse(xml_bytes)
       
       elif strategy == BPMNParsingStrategy.SPIFF_PREFERRED:
           return spiff_parse(xml_bytes)  # Will raise if SpiffWorkflow unavailable
       
       else:  # SPIFF_WITH_FALLBACK
           try:
               return spiff_parse(xml_bytes)
           except Exception:
               return minimal_parse(xml_bytes)
   ```

2. **Update All BPMN Parse Calls**:
   - Replace direct calls to `parse_bpmn()` or `from_bpmn_xml()`
   - Use `parse_bpmn_xml()` with explicit strategy parameter
   - Document which strategy each call site uses and why

3. **Update Layout Parser**:
   - Modify `backend/bpmn_layout.py` to use unified parser or clearly document why it needs custom parsing

#### Task 3.2: Refactor AI Integration

**Goal**: Clear separation between Ollama direct and Marvin agent capabilities

**Steps**:
1. **Create AI Service Interface**:
   ```python
   # src/agentic_process_automation/core/ai_service.py
   from abc import ABC, abstractmethod
   from typing import List, Dict, Any, Optional
   from .config import config
   
   class AIService(ABC):
       @abstractmethod
       async def generate_process_xml(self, description: str, process_type: str) -> str:
           pass
       
       @abstractmethod
       async def refine_process(self, current_xml: str, feedback: str) -> str:
           pass
       
       @abstractmethod
       async def generate_questions(self, context: str) -> List[str]:
           pass
   
   class OllamaService(AIService):
       """Direct Ollama integration for basic chat."""
       # Implementation using existing ollama code
   
   class MarvinAgentService(AIService):
       """Marvin-based agents for sophisticated process modeling."""
       # Implementation using existing marvin code
   
   class AIServiceFactory:
       @staticmethod
       def create_service(service_type: str = "marvin") -> AIService:
           if service_type == "ollama":
               return OllamaService()
           elif service_type == "marvin":
               return MarvinAgentService()
           else:
               raise ValueError(f"Unknown AI service type: {service_type}")
   ```

2. **Update All AI Callers**:
   - Replace direct calls to `ai_chat()`, `agent_chat()`, `generate_process_xml()`
   - Use AIServiceFactory to get appropriate service
   - Document when to use which service type

### **PHASE 4: FINAL CLEANUP (Week 6)**

#### Task 4.1: Import Path Standardization

**Goal**: Consistent, predictable import patterns

**Steps**:
1. **Update `__init__.py` Files** to export main interfaces:
   ```python
   # src/agentic_process_automation/__init__.py
   from .config import config
   from .core.validation import validator, ValidationResult
   from .core.ai_service import AIServiceFactory
   from .core.adapters.parser import parse_bpmn_xml, BPMNParsingStrategy
   from .core.pir import PIR, PIRBuilder
   
   __all__ = [
       "config", "validator", "ValidationResult",
       "AIServiceFactory", "parse_bpmn_xml", "BPMNParsingStrategy",
       "PIR", "PIRBuilder"
   ]
   ```

2. **Establish Import Conventions**:
   ```python
   # For internal core modules (use relative imports):
   from ..config import config
   from .validation import validator
   
   # For external packages (use absolute imports):
   from agentic_process_automation import config, validator
   
   # For CLI tools (use absolute imports to core):
   from agentic_process_automation.core.validation import validator
   ```

3. **Document Import Patterns** in README.md

#### Task 4.2: Verification and Documentation

**Goal**: Ensure all consolidation works and is documented

**Steps**:
1. **Run Complete Test Suite**:
   ```bash
   uv run python -m pytest tests/ -v --tb=short
   ```

2. **Test All Entry Points**:
   ```bash
   # Test primary web app
   ./start.sh
   # Test Streamlit alternative
   python main.py
   # Test API directly
   python backend/main.py
   ```

3. **Update Documentation**:
   - Update FUNCTIONALITY_INVENTORY.md with new structure
   - Update README.md with simplified instructions
   - Add CONSOLIDATION_COMPLETED.md with before/after comparison

4. **Performance Verification**:
   - Measure startup times before/after
   - Verify no regression in functionality
   - Document any breaking changes

**Success Criteria**:
- ✅ No duplicate code or directories
- ✅ All tests pass
- ✅ All entry points work
- ✅ Clear import patterns established
- ✅ Configuration centralized
- ✅ Documentation updated

**Rollback Plan**: Keep git commits atomic for each task so any issues can be reverted individually.
