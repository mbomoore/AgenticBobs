import json
import pytest
from unittest.mock import MagicMock
from agentic_process_automation.core.unified_spec.models import WorkItem
from agentic_process_automation.core.unified_spec.executors import HumanExecutor, AgentExecutor, SystemExecutor, get_executor

def test_human_executor_file_logging(tmp_path):
    """Tests that the HumanExecutor logs tasks to a file."""
    task_file = tmp_path / "human_tasks.log"
    executor = HumanExecutor(task_file=str(task_file))
    work_item = WorkItem(work_unit_name="resolve_ticket_by_human", parameters={"ticket_id": 123})

    executor.execute(work_item)

    assert task_file.exists()
    with open(task_file) as f:
        log_content = f.read()
        log_data = json.loads(log_content)
        assert log_data["work_unit_name"] == "resolve_ticket_by_human"
        assert log_data["parameters"]["ticket_id"] == 123

def test_human_executor_in_memory_list():
    """Tests that the HumanExecutor adds tasks to an in-memory list."""
    task_list = []
    executor = HumanExecutor(task_list=task_list)
    work_item = WorkItem(work_unit_name="review_document", parameters={"doc_id": "abc"})

    executor.execute(work_item)

    assert len(task_list) == 1
    assert task_list[0]["work_unit_name"] == "review_document"
    assert task_list[0]["parameters"]["doc_id"] == "abc"

def test_agent_executor_llm_call(mocker):
    """Tests that the AgentExecutor makes a correct call to an LLM service."""
    # Mock the httpx.post call
    mock_post = mocker.patch("httpx.post")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "This is a test response."}
    mock_post.return_value = mock_response

    # Initialize the executor with a dummy URL
    executor = AgentExecutor(llm_api_url="https://api.testllm.com/chat")
    work_item = WorkItem(
        work_unit_name="generate_summary",
        parameters={"text": "This is a long document..."}
    )

    executor.execute(work_item)

    # Assert that httpx.post was called correctly
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.testllm.com/chat"

    # Check the structure of the prompt
    sent_data = kwargs["json"]
    assert sent_data["model"] is not None
    assert "generate_summary" in sent_data["messages"][0]["content"]
    assert "This is a long document..." in sent_data["messages"][0]["content"]

def test_get_executor_factory():
    """Tests the get_executor factory function."""
    # Test with no kwargs
    assert isinstance(get_executor("system"), SystemExecutor)

    # Test with kwargs for HumanExecutor
    task_list = []
    human_executor = get_executor("human", task_list=task_list)
    assert isinstance(human_executor, HumanExecutor)
    assert human_executor.task_list is task_list

    # Test with kwargs for AgentExecutor
    agent_executor = get_executor("ai_agent", llm_api_url="http://dummy.url")
    assert isinstance(agent_executor, AgentExecutor)
    assert agent_executor.llm_api_url == "http://dummy.url"

    with pytest.raises(ValueError):
        get_executor("non_existent_executor")

    # Test that HumanExecutor raises ValueError if no task list or file is provided
    with pytest.raises(ValueError):
        HumanExecutor()
