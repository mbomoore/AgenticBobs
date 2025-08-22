"""
FastAPI backend for The Bobs 2.0 application.
Provides API endpoints for chat, BPMN generation, and process validation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Literal

import marvin
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.adapters.bpmn import parse_bpmn
from core.pir import validate
from core.viz import pir_to_mermaid
from src.agentic_process_automation.cli.common import build_model
from src.agentic_process_automation.cli.detect_type import bob_1
from src.agentic_process_automation.cli.generate_xml import generate_process_xml, ProcessGenerationConfig
from src.agentic_process_automation.cli.generate_refinement_questions import generate_refinement_questions, RefinementQuestionsConfig

app = FastAPI(title="The Bobs 2.0 API", version="1.0.0")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Type for process generation
ProcessType = Literal["BPMN", "DMN", "CMMN", "ArchiMate"]

@dataclass
class ChatSession:
    """Represents a chat session with conversation state."""
    session_id: str
    messages: List[Dict[str, str]]
    process_type: Optional[ProcessType]
    bpmn_xml: Optional[str]
    thread: marvin.Thread
    small_model: Any
    large_model: Any

# In-memory session storage (in production, use Redis or database)
sessions: Dict[str, ChatSession] = {}

def get_or_create_session(session_id: Optional[str] = None) -> ChatSession:
    """Get existing session or create a new one."""
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    # Create new session
    new_session_id = session_id or str(uuid.uuid4())
    new_session = ChatSession(
        session_id=new_session_id,
        messages=[],
        process_type=None,
        bpmn_xml=None,
        thread=marvin.Thread(),
        small_model=build_model(model_name="qwen3:8b"),
        large_model=build_model(model_name="gpt-oss:20b")
    )
    sessions[new_session_id] = new_session
    return new_session

# Sample BPMN for testing
SAMPLE_BPMN = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs_Sample">
  <process id="Proc_Sample" isExecutable="false">
    <startEvent id="Start_1" name="Start" />
    <task id="Task_A" name="Analyze Requirements" />
    <exclusiveGateway id="Gw_1" name="Clear?" />
    <task id="Task_B" name="Clarify" />
    <task id="Task_C" name="Design" />
    <endEvent id="End_1" name="End" />

    <sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A" />
    <sequenceFlow id="f2" sourceRef="Task_A" targetRef="Gw_1" />
    <sequenceFlow id="f3" name="No" sourceRef="Gw_1" targetRef="Task_B" />
    <sequenceFlow id="f4" name="Yes" sourceRef="Gw_1" targetRef="Task_C" />
    <sequenceFlow id="f5" sourceRef="Task_B" targetRef="Task_C" />
    <sequenceFlow id="f6" sourceRef="Task_C" targetRef="End_1" />
  </process>
</definitions>'''

# Pydantic models for API request/response
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    session_id: str
    bpmn_xml: Optional[str] = None
    process_type: Optional[ProcessType] = None
    questions: List[str] = []

class BpmnValidationRequest(BaseModel):
    bpmn_xml: str

class BpmnValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    mermaid_diagram: Optional[str] = None

class SampleBpmnResponse(BaseModel):
    bpmn_xml: str

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "The Bobs 2.0 API is running!", "version": "1.0.0"}

@app.get("/api/sample-bpmn", response_model=SampleBpmnResponse)
async def get_sample_bpmn():
    """Get the sample BPMN XML for testing."""
    return SampleBpmnResponse(bpmn_xml=SAMPLE_BPMN)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat messages and generate BPMN processes using the marvin pipeline.
    """
    try:
        session = get_or_create_session(request.session_id)
        
        # Add user message to session
        session.messages.append({"role": "user", "content": request.message})
        
        # Determine if we need to detect process type first
        if session.process_type is None:
            # First interaction - detect process type
            detected_type = bob_1(session.small_model, request.message)
            # Ensure the detected type is valid
            if detected_type in ["BPMN", "DMN", "CMMN", "ArchiMate"]:
                session.process_type = detected_type
            else:
                session.process_type = "BPMN"  # Default fallback
            
            # Generate initial XML
            pgen_config = ProcessGenerationConfig(
                description_or_answers=request.message,
                process_type=session.process_type,  # type: ignore
                model=session.large_model
            )
            bpmn_result = generate_process_xml(pgen_config)
            session.bpmn_xml = bpmn_result
            
            # Generate response message
            response_message = f"I've detected that you want to create a {session.process_type} process. I've generated an initial process diagram based on your description."
            
            # Generate refinement questions
            questions_config = RefinementQuestionsConfig(
                description=request.message,
                process_type=session.process_type,  # type: ignore
                bpmn_xml=bpmn_result,
                model=session.small_model
            )
            questions = generate_refinement_questions(questions_config)
            
        else:
            # Follow-up interaction - refine existing process
            # Use the conversation history to refine the process
            conversation_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in session.messages[-5:]])
            
            pgen_config = ProcessGenerationConfig(
                description_or_answers=conversation_context,
                process_type=session.process_type,  # type: ignore
                model=session.large_model
            )
            bpmn_result = generate_process_xml(pgen_config)
            session.bpmn_xml = bpmn_result
            
            response_message = "I've updated the process based on your feedback."
            questions = []
        
        # Add assistant response to session
        session.messages.append({"role": "assistant", "content": response_message})
        
        return ChatResponse(
            message=response_message,
            session_id=session.session_id,
            bpmn_xml=session.bpmn_xml,
            process_type=session.process_type,
            questions=questions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process chat message: {str(e)}")

@app.post("/api/validate-bpmn", response_model=BpmnValidationResponse)
async def validate_bpmn(request: BpmnValidationRequest):
    """Validate BPMN XML and return validation results."""
    try:
        # Parse the BPMN XML
        pir_model = parse_bpmn(request.bpmn_xml)
        
        # Validate the PIR model
        errors, warnings = validate(pir_model)
        is_valid = len(errors) == 0
        
        # Generate Mermaid diagram if valid
        mermaid_diagram = None
        if is_valid:
            try:
                mermaid_diagram = pir_to_mermaid(pir_model)
            except Exception as e:
                warnings.append(f"Failed to generate Mermaid diagram: {str(e)}")
        
        return BpmnValidationResponse(
            is_valid=is_valid,
            errors=[str(error) for error in errors],
            warnings=[str(warning) for warning in warnings],
            mermaid_diagram=mermaid_diagram
        )
        
    except Exception as e:
        return BpmnValidationResponse(
            is_valid=False,
            errors=[f"Failed to parse BPMN: {str(e)}"],
            warnings=[],
            mermaid_diagram=None
        )

@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get all messages for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"messages": sessions[session_id].messages}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
    return {"message": "Session deleted"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "The Bobs 2.0 API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)