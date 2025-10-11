import asyncio
import os
from collections.abc import AsyncGenerator

import aiohttp
from cogency.core.protocols import LLM
from cogency.lib.llms.interrupt import interruptible
from cogency.lib.logger import logger
from cogency.lib.rotation import with_rotation


class GLM(LLM):
    def __init__(
        self,
        api_key: str = None,
        http_model: str = "glm-4.6",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        if api_key is None:
            api_key = os.environ.get("GLM_API_KEY")

        if not api_key:
            raise RuntimeError("No GLM API key found")
        self.api_key = api_key
        self.http_model = http_model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._session = None
        self._recent_content = []  # Track recent content for intelligent completion

    def _create_session(self):
        return aiohttp.ClientSession()

    async def generate(self, messages: list[dict]) -> str:
        async def _generate_with_key(api_key: str) -> str:
            try:
                if self._session is None or self._session.closed:
                    self._session = self._create_session()

                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

                data = {
                    "model": self.http_model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }

                url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
                timeout = aiohttp.ClientTimeout(total=120)
                async with self._session.post(
                    url, headers=headers, json=data, timeout=timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GLM API error {response.status}: {error_text}")
                        raise ConnectionError(f"GLM API {response.status}: {error_text}")

                    result = await response.json()
                    return result["choices"][0]["message"]["content"]

            except asyncio.TimeoutError:
                logger.error("GLM API request timed out")
                raise RuntimeError("GLM API request timed out") from None
            except aiohttp.ServerDisconnectedError:
                await self.close()
                raise RuntimeError("Server disconnected, session reset") from None
            except Exception as e:
                logger.error(f"GLM generate failed: {str(e)}")
                raise RuntimeError(f"GLM generate error: {str(e)}") from e

        return await with_rotation("glm", _generate_with_key)

    @interruptible
    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        async def _stream_with_key(api_key: str) -> AsyncGenerator[str, None]:
            try:
                import json

                if self._session is None or self._session.closed:
                    self._session = self._create_session()

                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

                data = {
                    "model": self.http_model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "stream": True,
                }

                logger.debug(f"GLM sending {len(messages)} messages")
                for i, m in enumerate(messages[-5:]):
                    logger.debug(f"  msg[{i}] {m.get('role')}: {m.get('content', '')[:80]}")

                url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
                timeout = aiohttp.ClientTimeout(total=120, sock_read=30)  # Longer timeouts
                async with self._session.post(
                    url, headers=headers, json=data, timeout=timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GLM API error {response.status}: {error_text}")
                        raise ConnectionError(f"GLM API {response.status}: {error_text}")

                    buffer = ""
                    try:
                        async for chunk in response.content.iter_any():
                            decoded = chunk.decode("utf-8")
                            logger.debug(f"GLM raw decoded chunk: {repr(decoded[:100])}")
                            buffer += decoded
                            logger.debug(f"GLM buffer len={len(buffer)}")

                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.rstrip()
                                logger.debug(f"GLM processed line: {repr(line[:100])}")

                                if not line.startswith("data: "):
                                    continue

                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    logger.debug("GLM stream: [DONE] received")
                                    # Intelligent completion: only inject §end if not mid-tool-call
                                    if self._should_inject_end():
                                        yield "§end"
                                    return

                                try:
                                    chunk_data = json.loads(data_str)
                                    choices = chunk_data.get("choices", [{}])
                                    if not choices:
                                        continue

                                    choice = choices[0]
                                    delta = choice.get("delta", {})

                                    content = delta.get("content", "")
                                    if content:
                                        # Track recent content for intelligent completion detection
                                        self._recent_content.append(content)
                                        if (
                                            len(self._recent_content) > 10
                                        ):  # Keep only recent content
                                            self._recent_content.pop(0)

                                        logger.debug(f"GLM yielding content: {repr(content[:50])}")
                                        yield content
                                except json.JSONDecodeError as e:
                                    logger.debug(f"GLM JSON decode error: {e}")
                                    continue
                    except asyncio.CancelledError:
                        logger.debug("GLM stream cancelled")
                        raise

            except asyncio.TimeoutError:
                logger.error("GLM API stream timed out")
                raise RuntimeError("GLM API stream timed out") from None
            except aiohttp.ServerDisconnectedError:
                await self.close()
                raise RuntimeError("Server disconnected, session reset") from None
            except Exception as e:
                logger.error(f"GLM streaming failed: {str(e)}")
                raise RuntimeError(f"GLM streaming error: {str(e)}") from e

        async for chunk in _stream_with_key(self.api_key):
            yield chunk

    async def connect(self, messages: list[dict]) -> "LLM":
        raise NotImplementedError("GLM does not support WebSocket sessions")

    async def send(self, content: str) -> AsyncGenerator[str, None]:
        raise NotImplementedError("GLM does not support WebSocket sessions")

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("GLM HTTP session closed")
        self._session = None

    def _should_inject_end(self) -> bool:
        """Determine if we should inject §end based on recent content.

        Returns False if we detect an incomplete tool call (§call without §execute),
        True otherwise.
        """
        recent_text = "".join(self._recent_content)

        # Find the last §call and check if it has a corresponding §execute after it
        last_call_pos = recent_text.rfind("§call:")
        if last_call_pos == -1:
            # No tool calls at all
            logger.debug("GLM: No tool calls detected, injecting §end")
            return True

        # Check if there's a §execute after the last §call
        execute_after_last_call = "§execute" in recent_text[last_call_pos:]

        if not execute_after_last_call:
            # Last tool call is incomplete
            logger.debug("GLM: Detected incomplete tool call, not injecting §end")
            return False
        # Last tool call is complete or no tool calls
        logger.debug("GLM: No incomplete tool calls, injecting §end")
        return True
