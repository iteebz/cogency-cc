from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc.llms.codex import Codex


# Mock classes to simulate the OpenAI Responses API behavior for tool calls
class MockToolCall:
    def __init__(self, input_data, call_id, tool_type="custom", name="calculator"):
        self.input = input_data
        self.call_id = call_id
        self.type = tool_type
        self.name = name


class MockResponse:
    def __init__(self, output_list, response_id="mock_response_id"):
        self.output = output_list
        self.id = response_id


class MockAsyncOpenAI:
    def __init__(self):
        self.responses = MagicMock()
        self.responses.create = AsyncMock()


@pytest.fixture
def mock_openai_client():
    """Fixture to mock the OpenAI client."""
    with patch("openai.AsyncOpenAI", return_value=MockAsyncOpenAI()) as mock_client:
        yield mock_client


@pytest.mark.asyncio
async def test_codex_generate_with_tool_call(mock_openai_client):
    """
    Tests that Codex.generate correctly handles a tool call response.
    This test assumes Codex.generate is modified to return the tool call object.
    """
    # Arrange
    api_key = "test_api_key"
    model_name = "gpt-5-codex"
    Codex(api_key=api_key, model=model_name)

    expected_tool_call = MockToolCall({"expression": "2+2"}, "call_123")
    MockResponse([MagicMock(tool_calls=[expected_tool_call])])
