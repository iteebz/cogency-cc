"""Pytest configuration and fixtures for cogency-cc testing."""

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from cogency.core.protocols import LLM
from typer.testing import CliRunner


class MockLLM(LLM):
    def __init__(self, api_key: str = "mock-key"):
        self.api_key = api_key
        self.call_count = 0

    async def generate(self, messages: list[dict]) -> str:
        self.call_count += 1
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

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
        response = await self.generate(messages)
        for char in response:
            yield char

    async def connect(self, messages: list[dict]) -> "LLM":
        return self

    async def send(self, content: str) -> AsyncGenerator[str, None]:
        async for chunk in self.stream([{"role": "user", "content": content}]):
            yield chunk

    async def close(self) -> None:
        pass


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def mock_api_keys():
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
    from cc.lib.sqlite import DB

    DB._initialized_paths.clear()
    yield
    DB._initialized_paths.clear()


@pytest.fixture
def mock_config(tmp_path):
    from unittest.mock import Mock

    config = Mock()
    config.conversation_id = None
    config.user_id = "test_user"
    config.debug_mode = False
    config.config_dir = tmp_path / ".cogency"
    config.config_dir.mkdir(exist_ok=True)
    return config


@pytest.fixture
def mock_snapshots():
    from unittest.mock import Mock

    return Mock()
