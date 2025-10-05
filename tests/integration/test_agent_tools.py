"""Test agent tool usage with mock LLM."""

import asyncio
from unittest.mock import patch

import pytest

from cc.agent import create_agent
from cc.state import Config
from tests.conftest import MockLLM


def test_agent_with_mock_llm():
    """Test that agent can use tools when provided with mock LLM."""
    config = Config(provider="mock", user_id="test")
    config.identity = "coding"

    # Replace the GLM provider with our mock
    with patch("cc.agent._create_llm") as mock_create:
        mock_create.return_value = MockLLM()
        agent = create_agent(config)

        # Verify agent was created
        assert agent is not None
        assert hasattr(agent, "config")


@pytest.mark.asyncio
async def test_agent_tool_execution():
    """Test that agent properly executes tools when given a query."""
    config = Config(provider="mock", user_id="test")
    config.identity = "coding"

    with patch("cc.agent._create_llm") as mock_create:
        mock_llm = MockLLM()
        mock_create.return_value = mock_llm

        agent = create_agent(config)

        # Test with a query that should trigger directory listing
        events = []
        async for event in agent(
            query="list the files in this directory", user_id="test", conversation_id="test-conv"
        ):
            events.append(event)

        # Should have multiple events (respond, execute_tool, etc.)
        assert len(events) > 0

        # Check if we got any tool execution events
        tool_events = [e for e in events if e.get("type") == "execute_tool"]
        respond_events = [e for e in events if e.get("type") == "respond"]

        assert len(respond_events) > 0, "Should have at least one respond event"

        print(f"Total events: {len(events)}")
        print(f"Tool events: {len(tool_events)}")
        print(f"Respond events: {len(respond_events)}")

        # Print all events for debugging
        for i, event in enumerate(events):
            print(f"Event {i}: {event}")
            if event.get("type") == "respond":
                content = event.get("content", "")
                print(f"  Content has §execute: {'§execute' in content}")
                print(f"  Content repr: {repr(content)}")


if __name__ == "__main__":
    # Run a quick test
    asyncio.run(test_agent_tool_execution())
