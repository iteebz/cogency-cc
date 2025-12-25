import asyncio
import json
import os
from collections.abc import AsyncGenerator

import logging

import aiohttp
from cogency.core.protocols import LLM
from cogency.lib.llms.interrupt import interruptible

logger = logging.getLogger(__name__)


class MLX(LLM):
    def __init__(
        self,
        api_key: str = None,
        http_model: str = "mlx-community/Qwen3-8B-4bit",
        base_url: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or "not-needed"
        self.http_model = http_model
        self.base_url = base_url or os.environ.get("MLX_BASE_URL", "http://localhost:8080")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._session = None

    def _create_session(self):
        return aiohttp.ClientSession()

    async def generate(self, messages: list[dict]) -> str:
        try:
            if self._session is None or self._session.closed:
                self._session = self._create_session()

            headers = {"Content-Type": "application/json"}

            data = {
                "model": self.http_model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            url = f"{self.base_url}/v1/chat/completions"
            timeout = aiohttp.ClientTimeout(total=300, connect=30)
            async with self._session.post(
                url, headers=headers, json=data, timeout=timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"MLX API error {response.status}: {error_text}")
                    raise ConnectionError(f"MLX API {response.status}: {error_text}")

                result = await response.json()
                return result["choices"][0]["message"]["content"]

        except asyncio.TimeoutError as e:
            logger.error("MLX API request timed out")
            raise RuntimeError("MLX API request timed out") from e
        except aiohttp.ClientConnectorError as e:
            logger.error(f"MLX server not reachable at {self.base_url}")
            raise RuntimeError(f"MLX server not reachable: {e}") from e
        except Exception as e:
            logger.error(f"MLX generate failed: {str(e)}")
            raise RuntimeError(f"MLX generate error: {str(e)}") from e

    @interruptible
    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        try:
            if self._session is None or self._session.closed:
                self._session = self._create_session()

            headers = {"Content-Type": "application/json"}

            data = {
                "model": self.http_model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
            }

            if logger.isEnabledFor(10):
                logger.debug(f"MLX sending {len(messages)} messages")

            url = f"{self.base_url}/v1/chat/completions"
            timeout = aiohttp.ClientTimeout(total=300, sock_read=60, connect=30)
            async with self._session.post(
                url, headers=headers, json=data, timeout=timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"MLX API error {response.status}: {error_text}")
                    raise ConnectionError(f"MLX API {response.status}: {error_text}")

                buffer = ""
                stream_ended = False
                async for chunk in response.content.iter_any():
                    decoded = chunk.decode("utf-8")
                    buffer += decoded

                    while "\n" in buffer and not stream_ended:
                        line, buffer = buffer.split("\n", 1)
                        line = line.rstrip()

                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        if data_str == "[DONE]":
                            stream_ended = True
                            break

                        try:
                            chunk_data = json.loads(data_str)
                            choices = chunk_data.get("choices", [{}])
                            if not choices:
                                continue

                            choice = choices[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

                    if stream_ended:
                        break

        except asyncio.TimeoutError as e:
            logger.error("MLX API stream timed out")
            raise RuntimeError("MLX API stream timed out") from e
        except aiohttp.ClientConnectorError as e:
            logger.error(f"MLX server not reachable at {self.base_url}")
            raise RuntimeError(f"MLX server not reachable: {e}") from e
        except Exception as e:
            logger.error(f"MLX streaming failed: {str(e)}")
            raise RuntimeError(f"MLX streaming error: {str(e)}") from e

    async def connect(self, messages: list[dict]) -> "LLM":
        raise NotImplementedError("MLX does not support WebSocket sessions")

    async def send(self, content: str) -> AsyncGenerator[str, None]:
        raise NotImplementedError("MLX does not support WebSocket sessions")

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("MLX HTTP session closed")
        self._session = None
