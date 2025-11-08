from abc import ABC, abstractmethod
from .models import WorkItem
import json
import logging

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
    An executor that simulates a human picking up the work by logging it to a file.
    """
    def __init__(self, task_file: str = "human_tasks.log"):
        self.task_file = task_file

    def execute(self, work_item: WorkItem):
        """Logs the work item to a file."""
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
    def execute(self, work_item: WorkItem):
        """
        Formats the input views into a prompt for an LLM and executes the tool call.
        (This is a placeholder for the actual implementation).
        """
        logger.info(f"AgentExecutor: Executing WorkItem '{work_item.work_unit_name}' with parameters {work_item.parameters}")
        # In a real implementation, this would call the AI service.
        # For now, we just log it.
        pass

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

def get_executor(name: str) -> Executor:
    """Factory function to get an executor instance by name."""
    executors = {
        "human": HumanExecutor,
        "ai_agent": AgentExecutor,
        "system": SystemExecutor,
    }
    executor_class = executors.get(name)
    if not executor_class:
        raise ValueError(f"Unknown executor: {name}")
    return executor_class()
