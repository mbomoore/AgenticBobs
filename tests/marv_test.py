import marvin
import pytest
from icecream import ic
import os



pytestmark = pytest.mark.agent


def _configure_marvin_for_ollama():
    """Configure Marvin to work with local Ollama server."""
    # Set up environment variables for Ollama compatibility
    os.environ.setdefault("OPENAI_API_KEY", "dummy-key")  # Ollama doesn't need real key
    os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:11434/v1")

def test_marvin_agent():
    
    _configure_marvin_for_ollama()


    mv = marvin.Agent(name="marvin", model="openai:qwen3:4b")


    response = mv.say("What is the meaning of life?")
    
    ic(response)

    assert response is not None
    
    
    
def test_bpmn_writer():

    _configure_marvin_for_ollama()

    mv = marvin.Agent(name="BPMNWriter",
                      description="Agent that writes BPMN diagrams",
                      instructions="You are a BPMN writer agent. Your job is to generate correct BPMN diagrams that describe business processes.",
                      model = "openai:qwen3:4b",
    )
                      
                      
                      

    response = mv.say("What is the meaning of life?")

    ic(response)

    assert response is not None
