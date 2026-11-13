"""Pydantic schema enforcement with automated 1-retry self-correction."""

import json
from typing import Any, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class StructuredOutputWrapper:
    """Enforces strict Pydantic output schemas with an automatic 1-retry repair cycle."""

    def __init__(self, model: BaseChatModel) -> None:
        self.model = model

    def invoke_with_retry(
        self,
        schema: type[T],
        messages: list[Any],
        max_retries: int = 1,
    ) -> T:
        """Invoke the chat model and validate response against schema, retrying once on failure."""
        # Attempt 1: Using model.with_structured_output if supported
        try:
            structured_model = self.model.with_structured_output(schema)
            res = structured_model.invoke(messages)
            if isinstance(res, schema):
                return res
            if isinstance(res, dict):
                return schema.model_validate(res)
        except Exception as first_err:
            last_error = str(first_err)

            # Retry loop: feed validation error back to model for repair
            retry_messages = list(messages)
            for attempt in range(max_retries):
                repair_prompt = (
                    f"Your previous response failed schema validation for {schema.__name__}.\n"
                    f"Error details: {last_error}\n"
                    f"Please output ONLY a valid JSON object strictly conforming to schema:\n"
                    f"{json.dumps(schema.model_json_schema(), indent=2)}"
                )
                retry_messages.append(HumanMessage(content=repair_prompt))

                try:
                    response = self.model.invoke(retry_messages)
                    content = response.content if isinstance(response, AIMessage) else str(response)

                    # Extract JSON block if wrapped in markdown code fence
                    clean_json = self._extract_json(content)
                    data = json.loads(clean_json)
                    return schema.model_validate(data)
                except (ValidationError, json.JSONDecodeError, Exception) as retry_err:
                    last_error = str(retry_err)

            raise ValueError(
                f"Failed to produce valid structured output for {schema.__name__} after "
                f"{max_retries + 1} attempts. Last error: {last_error}"
            )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON payload from markdown backticks or raw text."""
        text = text.strip()
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.rindex("```")
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.rindex("```")
            return text[start:end].strip()
        return text


def with_structured_retry(
    model: BaseChatModel,
    schema: type[T],
    messages: list[Any],
    max_retries: int = 1,
) -> T:
    """Convenience functional helper for structured invocation with self-correction."""
    wrapper = StructuredOutputWrapper(model)
    return wrapper.invoke_with_retry(schema, messages, max_retries=max_retries)

