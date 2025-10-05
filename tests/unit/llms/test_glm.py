"""GLM provider tests."""

from unittest.mock import patch

import pytest

from cc.llms.glm import GLM


def test_initialization():
    """Test GLM provider initialization."""
    glm = GLM()

    assert glm.api_key is not None
    assert glm.http_model == "GLM-4.6"
    assert glm.temperature == 0.7
    assert glm.max_tokens == 4096


def test_initialization_with_custom_key():
    """Test GLM initialization with custom API key."""
    glm = GLM(api_key="custom_key")

    assert glm.api_key == "custom_key"


def test_session_creation():
    """Test GLM session creation."""
    glm = GLM(api_key="test_key")

    # Session should be None initially
    assert glm._session is None

    # Session creation method exists
    assert hasattr(glm, "_create_session")


def test_config_parameters():
    """Test GLM configuration parameters."""
    glm = GLM(api_key="test_key", http_model="GLM-4", temperature=0.5, max_tokens=2048)

    assert glm.api_key == "test_key"
    assert glm.http_model == "GLM-4"
    assert glm.temperature == 0.5
    assert glm.max_tokens == 2048


def test_no_api_key_error():
    """Test GLM raises error without API key."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="No GLM API key found"):
            GLM()


def test_env_key():
    """Test GLM picks up API key from environment."""
    with patch.dict("os.environ", {"GLM_API_KEY": "env_key_test"}):
        glm = GLM()
        assert glm.api_key == "env_key_test"


@pytest.mark.asyncio
async def test_generate_method():
    """Test GLM generate method exists and is async."""
    glm = GLM(api_key="test_key")

    # Method should exist
    assert hasattr(glm, "generate")
    assert callable(glm.generate)

    # Method should be async
    import inspect

    assert inspect.iscoroutinefunction(glm.generate)


@pytest.mark.asyncio
async def test_stream_method():
    """Test GLM stream method exists and is async."""
    glm = GLM(api_key="test_key")

    # Method should exist
    assert hasattr(glm, "stream")
    assert callable(glm.stream)

    # Method should be async generator
    import inspect

    assert inspect.isasyncgenfunction(glm.stream)


@pytest.mark.asyncio
async def test_stream_no_duplicates():
    """Test GLM stream doesn't emit duplicate chunks."""
    from unittest.mock import AsyncMock, MagicMock, patch

    glm = GLM(api_key="test_key")

    # Mock SSE response chunks
    mock_chunks = [
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
        b'data: {"choices":[{"delta":{"content":" world"}}]}\n',
        b"data: [DONE]\n",
    ]

    async def mock_iter():
        for chunk in mock_chunks:
            yield chunk

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content.iter_any = mock_iter

    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)

    glm._session = mock_session

    with patch("cc.llms.glm.with_rotation") as mock_rotation:

        async def mock_rot(key, fn):
            async for chunk in fn("test_key"):
                yield chunk

        mock_rotation.side_effect = mock_rot

        chunks = []
        async for chunk in glm.stream([{"role": "user", "content": "test"}]):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]
        assert len(chunks) == 2
