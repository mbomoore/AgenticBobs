"""Concrete AI service implementation using Marvin."""
from __future__ import annotations

import marvin
from .services import AIService
from .common import build_model, get_empty_process_model
from ..config import get_ai_config

class MarvinAIService(AIService):
    """
    An AI service that uses Marvin Agents to generate and refine process diagrams.
    """

    async def generate_process_xml(self, description: str, process_type: str) -> str:
        """
        Generates process XML from a natural language description.
        """
        ai_config = get_ai_config()
        model = build_model(model_name=ai_config.default_large_model)

        empty_template, example_inputs = get_empty_process_model(process_type)
        base_xml = empty_template.format(**example_inputs)

        return await self._run_marvin_task(description, process_type, model, base_xml)

    async def refine_process(self, current_xml: str, feedback: str) -> str:
        """
        Refines an existing process XML based on user feedback.
        """
        ai_config = get_ai_config()
        model = build_model(model_name=ai_config.default_large_model)

        # The description for the task is the user's feedback
        return await self._run_marvin_task(feedback, "BPMN", model, current_xml) # Assuming BPMN for now

    async def _run_marvin_task(self, description: str, process_type: str, model, base_xml: str) -> str:
        """Helper to run the core Marvin agent task."""
        bob_2 = marvin.Agent(
            name="Bob_2",
            model=model,
            instructions=(
                f"You are an expert {process_type} diagram generator. "
                f"Your ONLY job is to output complete, valid {process_type} XML. "
                f"CRITICAL RULES:\n"
                f"1. Return ONLY XML starting with <?xml version=\n"
                f"2. NO explanations, NO descriptions, NO text before or after the XML\n"
                f"3. Modify the provided template to match the business process description\n"
                f"4. Ensure all element IDs are unique and properly referenced\n"
                f"5. Your response must be parseable by an XML parser\n"
                f"6. NEVER explain what you changed - just return the XML\n\n"
                f"Input: Template XML + Business process description\n"
                f"Output: Complete {process_type} XML (nothing else)"
            ),
            tools=[],
        )

        task_context = {
            "description": description,
            "xml_process": base_xml,
        }

        xml_task = marvin.Task(
            "Make the necessary changes to the XML diagram to align it with the described business process",
            agents=[bob_2],
            context=task_context,
        )

        generated_xml = await xml_task.run()

        # Basic cleanup and validation
        result_xml = str(generated_xml).strip()
        if not result_xml.startswith('<?xml'):
            # In a real scenario, you might want more robust error handling or extraction
            # For now, if it's not valid, we might return the base_xml or raise an error
            raise ValueError("AI failed to generate valid XML.")

        return result_xml
