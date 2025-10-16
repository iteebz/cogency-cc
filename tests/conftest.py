"""Pytest configuration and fixtures for cogency-cc testing."""

import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from cogency.core.protocols import LLM
from typer.testing import CliRunner


class MockLLM(LLM):
    """A mock LLM that returns predefined responses for testing."""

    def __init__(self, api_key: str = "mock-key"):
        self.api_key = api_key
        self.call_count = 0

    async def generate(self, messages: list[dict]) -> str:
        """Generate a mock response."""
        self.call_count += 1

        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        print(f"Mock LLM received messages: {messages}")
        print(f"User message extracted: {repr(user_message)}")
        print(f"Contains 'directory': {'directory' in user_message.lower()}")
        print(f"Contains 'files': {'files' in user_message.lower()}")

        # Simple mock responses that include tool usage
        if "directory" in user_message.lower() or "files" in user_message.lower():
            return """I'll help you list the files in the current directory.

§execute
{"tool": "bash", "command": "ls -la"}"""

        if "read" in user_message.lower() and "readme" in user_message.lower():
            return """I'll read the README.md file for you.

§execute
{"tool": "view", "file_path": "README.md"}"""

        return """I understand your request. Let me help you with that.

§execute
{"tool": "bash", "command": "echo 'Hello from mock LLM'"}"""

    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Stream a mock response."""
        response = await self.generate(messages)
        for char in response:
            yield char

    async def connect(self, messages: list[dict]) -> "LLM":
        """Mock connection - not used for this simple test."""
        return self

    async def send(self, content: str) -> AsyncGenerator[str, None]:
        """Mock send - not used for this simple test."""
        async for chunk in self.stream([{"role": "user", "content": content}]):
            yield chunk

    async def close(self) -> None:
        """Mock close - no cleanup needed."""
        pass


@pytest.fixture
def cli_runner():
    """Fixture providing a typer CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def mock_llm():
    """Fixture providing a mock LLM for testing."""
    return MockLLM()


@pytest.fixture
def mock_api_keys():
    """Fixture providing mock API keys for all providers."""
    with patch.dict(
        "os.environ",
        {
            "GLM_API_KEY": "test-glm-key",
            "OPENAI_API_KEY": "test-openai-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "GEMINI_API_KEY": "test-gemini-key",
        },
    ):
        yield


@pytest.fixture
def clear_db_initialized_paths():
    """Fixture to clear the DB._initialized_paths before each test."""
    from cc.lib.sqlite import DB

    DB._initialized_paths.clear()
    yield
    DB._initialized_paths.clear()


@pytest.fixture
def clean_config_file(tmp_path, clear_db_initialized_paths):
    cogency_dir = tmp_path / ".cogency"
    cogency_dir.mkdir(exist_ok=True)
    config_file = cogency_dir / "cc.json"
    db_file = cogency_dir / "store.db"

    if config_file.exists():
        os.remove(config_file)
    if db_file.exists():
        os.remove(db_file)
    return config_file
