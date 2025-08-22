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

ProcessType = Literal["BPMN", "DMN", "CMMN", "ArchiMate"]

@dataclass
class ChatSession:
    """Represents a chat session with state for conversation continuity."""
    session_id: str
    messages: List[dict]
    thread: marvin.Thread
    process_type: Optional[str] = None  # Changed to str to avoid type issues
    current_xml: Optional[str] = None
    small_model: Optional[Any] = None
    large_model: Optional[Any] = None

# In-memory session storage (in production, use Redis or database)
sessions: Dict[str, ChatSession] = {}

def get_or_create_session(session_id: Optional[str] = None) -> ChatSession:
    """Get existing session or create a new one."""
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    new_session_id = session_id or str(uuid.uuid4())
    new_session = ChatSession(
        session_id=new_session_id,
        messages=[],
        thread=marvin.Thread(),
        small_model=build_model(model_name="qwen3:8b"),
        large_model=build_model(model_name="gpt-oss:20b")
    )
    sessions[new_session_id] = new_session
    return new_session

# Sample BPMN for testing
SAMPLE_BPMN = """# Sample BPMN for testing
SAMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" 
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             id="Defs_Sample">
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
</definitions>"""

# Pydantic models for API request/response"""
    <bpmn2:startEvent id="StartEvent_1" name="Start">
      <bpmn2:outgoing>SequenceFlow_1</bpmn2:outgoing>
    </bpmn2:startEvent>
    <bpmn2:task id="Task_1" name="Analyze Requirements">
      <bpmn2:incoming>SequenceFlow_1</bpmn2:incoming>
      <bpmn2:outgoing>SequenceFlow_2</bpmn2:outgoing>
    </bpmn2:task>
    <bpmn2:exclusiveGateway id="Gateway_1" name="Requirements Clear?">
      <bpmn2:incoming>SequenceFlow_2</bpmn2:incoming>
      <bpmn2:outgoing>SequenceFlow_3</bpmn2:outgoing>
      <bpmn2:outgoing>SequenceFlow_4</bpmn2:outgoing>
    </bpmn2:exclusiveGateway>
    <bpmn2:task id="Task_2" name="Request Clarification">
      <bpmn2:incoming>SequenceFlow_3</bpmn2:incoming>
      <bpmn2:outgoing>SequenceFlow_5</bpmn2:outgoing>
    </bpmn2:task>
    <bpmn2:task id="Task_3" name="Design Solution">
      <bpmn2:incoming>SequenceFlow_4</bpmn2:incoming>
      <bpmn2:incoming>SequenceFlow_5</bpmn2:incoming>
      <bpmn2:outgoing>SequenceFlow_6</bpmn2:outgoing>
    </bpmn2:task>
    <bpmn2:endEvent id="EndEvent_1" name="End">
      <bpmn2:incoming>SequenceFlow_6</bpmn2:incoming>
    </bpmn2:endEvent>
    <bpmn2:sequenceFlow id="SequenceFlow_1" sourceRef="StartEvent_1" targetRef="Task_1"/>
    <bpmn2:sequenceFlow id="SequenceFlow_2" sourceRef="Task_1" targetRef="Gateway_1"/>
    <bpmn2:sequenceFlow id="SequenceFlow_3" name="No" sourceRef="Gateway_1" targetRef="Task_2"/>
    <bpmn2:sequenceFlow id="SequenceFlow_4" name="Yes" sourceRef="Gateway_1" targetRef="Task_3"/>
    <bpmn2:sequenceFlow id="SequenceFlow_5" sourceRef="Task_2" targetRef="Task_3"/>
    <bpmn2:sequenceFlow id="SequenceFlow_6" sourceRef="Task_3" targetRef="EndEvent_1"/>
  </bpmn2:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
        <dc:Bounds x="152" y="102" width="36" height="36"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="158" y="145" width="24" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">
        <dc:Bounds x="240" y="80" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_1_di" bpmnElement="Gateway_1" isMarkerVisible="true">
        <dc:Bounds x="395" y="95" width="50" height="50"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="378" y="65" width="84" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_2_di" bpmnElement="Task_2">
        <dc:Bounds x="370" y="200" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_3_di" bpmnElement="Task_3">
        <dc:Bounds x="520" y="80" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">
        <dc:Bounds x="672" y="102" width="36" height="36"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="680" y="145" width="20" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="SequenceFlow_1_di" bpmnElement="SequenceFlow_1">
        <di:waypoint x="188" y="120"/>
        <di:waypoint x="240" y="120"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_2_di" bpmnElement="SequenceFlow_2">
        <di:waypoint x="340" y="120"/>
        <di:waypoint x="395" y="120"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_3_di" bpmnElement="SequenceFlow_3">
        <di:waypoint x="420" y="145"/>
        <di:waypoint x="420" y="200"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="428" y="170" width="15" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_4_di" bpmnElement="SequenceFlow_4">
        <di:waypoint x="445" y="120"/>
        <di:waypoint x="520" y="120"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="475" y="102" width="18" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_5_di" bpmnElement="SequenceFlow_5">
        <di:waypoint x="470" y="240"/>
        <di:waypoint x="570" y="240"/>
        <di:waypoint x="570" y="160"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_6_di" bpmnElement="SequenceFlow_6">
        <di:waypoint x="620" y="120"/>
        <di:waypoint x="672" y="120"/>
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn2:definitions>"""
      <bpmn2:outgoing>SequenceFlow_2</bpmn2:outgoing>
    </bpmn2:task>
    <bpmn2:exclusiveGateway id="Gateway_1" name="Requirements Clear?">
      <bpmn2:incoming>SequenceFlow_2</bpmn2:incoming>
      <bpmn2:outgoing>SequenceFlow_3</bpmn2:outgoing>
      <bpmn2:outgoing>SequenceFlow_4</bpmn2:outgoing>
    </bpmn2:exclusiveGateway>
    <bpmn2:task id="Task_2" name="Request Clarification">
      <bpmn2:incoming>SequenceFlow_3</bpmn2:incoming>
      <bpmn2:outgoing>SequenceFlow_5</bpmn2:outgoing>
    </bpmn2:task>
    <bpmn2:task id="Task_3" name="Design Solution">
      <bpmn2:incoming>SequenceFlow_4</bpmn2:incoming>
      <bpmn2:incoming>SequenceFlow_5</bpmn2:incoming>
      <bpmn2:outgoing>SequenceFlow_6</bpmn2:outgoing>
    </bpmn2:task>
    <bpmn2:endEvent id="EndEvent_1" name="End">
      <bpmn2:incoming>SequenceFlow_6</bpmn2:incoming>
    </bpmn2:endEvent>
    <bpmn2:sequenceFlow id="SequenceFlow_1" sourceRef="StartEvent_1" targetRef="Task_1"/>
    <bpmn2:sequenceFlow id="SequenceFlow_2" sourceRef="Task_1" targetRef="Gateway_1"/>
    <bpmn2:sequenceFlow id="SequenceFlow_3" name="No" sourceRef="Gateway_1" targetRef="Task_2"/>
    <bpmn2:sequenceFlow id="SequenceFlow_4" name="Yes" sourceRef="Gateway_1" targetRef="Task_3"/>
    <bpmn2:sequenceFlow id="SequenceFlow_5" sourceRef="Task_2" targetRef="Task_3"/>
    <bpmn2:sequenceFlow id="SequenceFlow_6" sourceRef="Task_3" targetRef="EndEvent_1"/>
  </bpmn2:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
        <dc:Bounds x="152" y="102" width="36" height="36"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="158" y="145" width="24" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">
        <dc:Bounds x="240" y="80" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_1_di" bpmnElement="Gateway_1" isMarkerVisible="true">
        <dc:Bounds x="395" y="95" width="50" height="50"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="378" y="65" width="84" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_2_di" bpmnElement="Task_2">
        <dc:Bounds x="370" y="200" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_3_di" bpmnElement="Task_3">
        <dc:Bounds x="520" y="80" width="100" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">
        <dc:Bounds x="672" y="102" width="36" height="36"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="680" y="145" width="20" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="SequenceFlow_1_di" bpmnElement="SequenceFlow_1">
        <di:waypoint x="188" y="120"/>
        <di:waypoint x="240" y="120"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_2_di" bpmnElement="SequenceFlow_2">
        <di:waypoint x="340" y="120"/>
        <di:waypoint x="395" y="120"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_3_di" bpmnElement="SequenceFlow_3">
        <di:waypoint x="420" y="145"/>
        <di:waypoint x="420" y="200"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="428" y="170" width="15" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_4_di" bpmnElement="SequenceFlow_4">
        <di:waypoint x="445" y="120"/>
        <di:waypoint x="520" y="120"/>
        <bpmndi:BPMNLabel>
          <dc:Bounds x="475" y="102" width="18" height="14"/>
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_5_di" bpmnElement="SequenceFlow_5">
        <di:waypoint x="470" y="240"/>
        <di:waypoint x="570" y="240"/>
        <di:waypoint x="570" y="160"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="SequenceFlow_6_di" bpmnElement="SequenceFlow_6">
        <di:waypoint x="620" y="120"/>
        <di:waypoint x="672" y="120"/>
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn2:definitions>"""

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
    return {"message": "The Bobs 2.0 API is running"}

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
                model_instance=session.large_model,
                current_thread=session.thread,
                current_xml=session.current_xml
            )
            
            result = generate_process_xml(pgen_config)
            session.current_xml = result.xml
            
            # Generate refinement questions
            rfc = RefinementQuestionsConfig(
                original_description_or_answer=request.message,
                generated_xml=session.current_xml,
                process_type=session.process_type,  # type: ignore
                model_instance=session.large_model,
                current_thread=session.thread
            )
            
            questions = generate_refinement_questions(rfc)
            
            assistant_message = "I've analyzed your process and created an initial model. Here are some questions to help refine it:"
            
            response = ChatResponse(
                message=assistant_message,
                session_id=session.session_id,
                bpmn_xml=session.current_xml,
                process_type=session.process_type,  # type: ignore
                questions=questions
            )
        else:
            # Continuing conversation - refine existing XML
            pgen_config = ProcessGenerationConfig(
                description_or_answers=request.message,
                process_type=session.process_type,  # type: ignore
                model_instance=session.large_model,
                current_thread=session.thread,
                current_xml=session.current_xml
            )
            
            result = generate_process_xml(pgen_config)
            session.current_xml = result.xml
            
            # Generate new refinement questions
            rfc = RefinementQuestionsConfig(
                original_description_or_answer=request.message,
                generated_xml=session.current_xml,
                process_type=session.process_type,  # type: ignore
                model_instance=session.large_model,
                current_thread=session.thread
            )
            
            questions = generate_refinement_questions(rfc)
            
            assistant_message = "I've updated the process model based on your input. Here are some follow-up questions:"
            
            response = ChatResponse(
                message=assistant_message,
                session_id=session.session_id,
                bpmn_xml=session.current_xml,
                process_type=session.process_type,  # type: ignore
                questions=questions
            )
        
        # Add assistant message to session
        session.messages.append({"role": "assistant", "content": response.message})
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing chat message: {str(e)}"
        )

@app.post("/api/validate-bpmn", response_model=BpmnValidationResponse)
async def validate_bpmn(request: BpmnValidationRequest):
    """
    Validate BPMN XML and generate Mermaid diagram.
    """
    try:
        if not request.bpmn_xml.strip():
            return BpmnValidationResponse(
                is_valid=False,
                errors=["Empty BPMN XML provided"],
                warnings=[],
                mermaid_diagram=None
            )
        
        # Parse BPMN and validate
        pir = parse_bpmn(request.bpmn_xml.encode("utf-8"))
        report = validate(pir)
        
        errors = report.get("errors", [])
        warnings = report.get("warnings", [])
        is_valid = len(errors) == 0
        
        mermaid_diagram = None
        if is_valid:
            try:
                mermaid_diagram = pir_to_mermaid(pir)
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
