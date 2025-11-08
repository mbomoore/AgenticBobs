from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import WorkItem
from ...config import get_ai_config
import json
import logging
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Executor(ABC):
    """Abstract base class for all executors."""
    @abstractmethod
    def execute(self, work_item: WorkItem):
        """Executes a work item."""
        pass

class HumanExecutor(Executor):
    """
    An executor that simulates a human picking up the work by adding it to a task list.
    """
    def __init__(self, task_list: Optional[List[Dict[str, Any]]] = None, task_file: Optional[str] = None):
        if task_list is None and task_file is None:
            raise ValueError("HumanExecutor must be initialized with either a task_list or a task_file.")
        self.task_list = task_list
        self.task_file = task_file

    def execute(self, work_item: WorkItem):
        """Adds the work item to the configured task list or file."""
        if self.task_list is not None:
            self.task_list.append(work_item.model_dump())
            logger.info(f"HumanExecutor: Added WorkItem '{work_item.work_unit_name}' to the in-memory task list.")

        if self.task_file:
            try:
                with open(self.task_file, "a") as f:
                    f.write(work_item.model_dump_json() + "\n")
                logger.info(f"HumanExecutor: Logged WorkItem '{work_item.work_unit_name}' to {self.task_file}")
            except IOError as e:
                logger.error(f"HumanExecutor: Error writing to task file {self.task_file}: {e}")
                raise

class AgentExecutor(Executor):
    """
    An executor that uses an AI agent to perform the work.
    """
    def __init__(self, llm_api_url: Optional[str] = None):
        ai_config = get_ai_config()
        self.llm_api_url = llm_api_url or ai_config.ollama_api_url
        self.model = ai_config.default_model

    def execute(self, work_item: WorkItem):
        """
        Formats the input views into a prompt for an LLM and executes the tool call.
        """
        logger.info(f"AgentExecutor: Executing WorkItem '{work_item.work_unit_name}' with parameters {work_item.parameters}")

        # Simple prompt generation for now
        prompt = f"Work Unit: {work_item.work_unit_name}\n"
        prompt += f"Parameters: {json.dumps(work_item.parameters, indent=2)}\n"
        prompt += f"Please generate a response for the above work unit."

        try:
            response = httpx.post(
                self.llm_api_url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            logger.info(f"AgentExecutor: Successfully received response from LLM: {response.json()}")
            # In a real implementation, we would process the response and update the case.
        except httpx.RequestError as e:
            logger.error(f"AgentExecutor: Error calling LLM API: {e}")
            raise

class SystemExecutor(Executor):
    """
    An executor for automated system tasks (e.g., sending an email).
    """
    def execute(self, work_item: WorkItem):
        """
        Executes a system-level task.
        (This is a placeholder for the actual implementation).
        """
        logger.info(f"SystemExecutor: Executing WorkItem '{work_item.work_unit_name}'")
        # In a real implementation, this would interact with other system components.
        # For now, we just log it.
        pass

def get_executor(name: str, **kwargs) -> Executor:
    """Factory function to get an executor instance by name."""
    executors = {
        "human": HumanExecutor,
        "ai_agent": AgentExecutor,
        "system": SystemExecutor,
    }
    executor_class = executors.get(name)
    if not executor_class:
        raise ValueError(f"Unknown executor: {name}")

    # Inject dependencies from kwargs if they match constructor arguments
    import inspect
    sig = inspect.signature(executor_class.__init__)
    valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

    return executor_class(**valid_kwargs)
