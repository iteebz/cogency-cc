"""GLM provider - LLM protocol implementation.

HTTP-only provider using the Coding API endpoint. WebSocket sessions not supported.
"""

from collections.abc import AsyncGenerator

from cogency.core.protocols import LLM
from cogency.lib.llms.interrupt import interruptible
from cogency.lib.logger import logger
from cogency.lib.rotation import get_api_key, with_rotation


class GLM(LLM):
    """GLM provider implementing HTTP-only LLM protocol with Coding API."""

    def __init__(
        self,
        api_key: str = None,
        http_model: str = "GLM-4.6",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ):
        self.api_key = api_key or get_api_key("glm")
        if not self.api_key:
            raise RuntimeError("No GLM API key found")
        self.http_model = http_model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # HTTP client session
        self._session = None

    def _create_session(self):
        """Create HTTP session for GLM API requests."""
        import aiohttp

        return aiohttp.ClientSession()

    async def generate(self, messages: list[dict]) -> str:
        """Generate complete response from conversation messages."""

        async def _generate_with_key(api_key: str) -> str:
            try:
                if self._session is None:
                    self._session = self._create_session()

                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

                data = {
                    "model": self.http_model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }

                url = "https://api.z.ai/api/coding/paas/v4/chat/completions"

                async with self._session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GLM API error {response.status}: {error_text}")
                        raise ConnectionError(f"GLM API {response.status}: {error_text}")

                    result = await response.json()
                    return result["choices"][0]["message"]["content"]

            except Exception as e:
                logger.error(f"GLM generate failed: {str(e)}")
                raise RuntimeError(f"GLM generate error: {str(e)}") from e

        return await with_rotation("glm", _generate_with_key)

    @interruptible
    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Generate streaming tokens from conversation messages."""

        async def _stream_with_key(api_key: str) -> AsyncGenerator[str, None]:
            try:
                import json

                if self._session is None:
                    self._session = self._create_session()

                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

                data = {
                    "model": self.http_model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "stream": True,
                }

                url = "https://api.z.ai/api/coding/paas/v4/chat/completions"

                async with self._session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GLM API error {response.status}: {error_text}")
                        raise ConnectionError(f"GLM API {response.status}: {error_text}")

                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # Remove 'data: ' prefix
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data_str)
                            if chunk_data.get("choices") and chunk_data["choices"][0].get(
                                "delta", {}
                            ).get("content"):
                                yield chunk_data["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            # Skip malformed JSON - expected in streaming
                            continue

            except Exception as e:
                logger.error(f"GLM streaming failed: {str(e)}")
                raise RuntimeError(f"GLM streaming error: {str(e)}") from e

        async for chunk in _stream_with_key(self.api_key):
            yield chunk

    # WebSocket methods - not supported by GLM API
    async def connect(self, messages: list[dict]) -> "LLM":
        """WebSocket sessions not supported by GLM API."""
        raise NotImplementedError("GLM does not support WebSocket sessions")

    async def send(self, content: str) -> AsyncGenerator[str, None]:
        """WebSocket sessions not supported by GLM API."""
        raise NotImplementedError("GLM does not support WebSocket sessions")

    async def close(self) -> None:
        """Clean up session resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("GLM HTTP session closed")
        self._session = None
