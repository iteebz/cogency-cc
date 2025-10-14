import json
from collections.abc import AsyncGenerator

from cogency.core.protocols import LLM
from cogency.lib.llms.rotation import get_api_key, with_rotation


class Codex(LLM):
    """OpenAI Codex provider using the Responses API."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-5-codex",
        temperature: float = 1.0,
        max_tokens: int = 2000,
        tools: list[dict] | None = None,
    ):
        self.api_key = api_key or get_api_key("openai")
        if not self.api_key:
            raise RuntimeError("No API key found for Codex")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tools = tools

    def _create_client(self, api_key: str):
        """Create OpenAI client for given API key."""
        import openai

        return openai.AsyncOpenAI(api_key=api_key)

    def _normalise_content(self, content) -> str:
        """Normalise assorted message payloads to a single text block."""
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                else:
                    parts.append(json.dumps(item))
            return "\n".join(parts)
        if isinstance(content, str):
            return content
        if content is None:
            return ""
        return json.dumps(content)

    def _format_messages(self, messages: list[dict]) -> list[dict]:
        """Convert chat-style messages into Responses API input."""
        formatted: list[dict] = []
        for message in messages:
            role = message.get("role")
            if not role:
                continue
            normalized = self._normalise_content(message.get("content", ""))
            if role == "assistant":
                content_type = "output_text"
            else:
                content_type = "input_text"
            formatted.append(
                {"role": role, "content": [{"type": content_type, "text": normalized}]}
            )
        return formatted

    def _prepare_tools(self, tools: list[dict] | None):
        """Ensure tool payload is serializable for Responses API."""
        if not tools:
            return None
        serializable: list[dict] = []
        for tool in tools:
            if isinstance(tool, dict):
                serializable.append(tool)
        return serializable or None

    @staticmethod
    def _extract_text(response) -> str:
        """Extract concatenated text from a Responses API result."""
        if response is None:
            return ""

        if hasattr(response, "output_text"):
            text = response.output_text
            if text:
                return text

        if hasattr(response, "to_dict"):
            response = response.to_dict()

        if isinstance(response, dict):
            fragments: list[str] = []
            for item in response.get("output", []):
                if not isinstance(item, dict):
                    continue
                content = item.get("content", [])
                if isinstance(content, list):
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        if part.get("type") in {"output_text", "text"}:
                            fragments.append(part.get("text") or "")
                elif isinstance(content, str):
                    fragments.append(content)
            if fragments:
                return "".join(fragments)

        return ""

    async def generate(self, messages: list[dict], tools: list[dict] | None = None) -> str:
        """One-shot completion with full conversation context using Responses API."""
        formatted_messages = self._format_messages(messages)
        tool_payload = self._prepare_tools(tools or self.tools)

        async def _generate_with_key(api_key: str) -> str:
            try:
                client = self._create_client(api_key)
                response = await client.responses.create(
                    model=self.model,
                    input=formatted_messages,
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    tools=tool_payload,
                )
                return self._extract_text(response)
            except ImportError as e:
                raise ImportError("Please install openai: pip install openai") from e
            except Exception as e:
                raise RuntimeError(f"Codex Generate Error: {str(e)}") from e

        return await with_rotation("OPENAI", _generate_with_key)

    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Streaming completion with full conversation context using Responses API (via generate)."""
        full_response = await self.generate(messages)
        if "§end" not in full_response:
            full_response += " §end"
        yield full_response

    async def connect(self, messages: list[dict]) -> "Codex":
        """Codex does not support WebSocket connections directly via this API."""
        raise NotImplementedError("Codex does not support WebSocket connections.")

    async def send(self, content: str) -> AsyncGenerator[str, None]:
        """Codex does not support sending messages in an active session directly via this API."""
        raise NotImplementedError("Codex does not support sending messages in an active session.")

    async def close(self) -> None:
        """No-op for Codex as there are no active connections to close."""
        pass
