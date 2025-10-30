"""GLM provider tests."""

from unittest.mock import patch

import pytest

from cc.llms.glm import GLM


def test_initialization(mock_api_keys):
    """Test GLM provider initialization."""
    glm = GLM()

    assert glm.api_key is not None
    assert glm.http_model == "glm-4.6"
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
    glm = GLM(api_key="test_key", http_model="glm-4", temperature=0.5, max_tokens=2048)

    assert glm.api_key == "test_key"
    assert glm.http_model == "glm-4"
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


@pytest.mark.asyncio
async def test_stream_handles_fragmented_sse_messages():
    """Test GLM properly reassembles SSE messages split across TCP packets."""
    from unittest.mock import AsyncMock, MagicMock, patch

    glm = GLM(api_key="test_key")

    # Mock fragmented TCP packets - this is what causes character-by-character streaming
    mock_chunks = [
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}',  # No newline - fragmented
        b"\n",  # Completed message
        b'data: {"choices":[{"delta":{"content":" world"}}]}\n',  # Complete message
        b'data: {"choices":[{"delta":{"content":"!"}}]}',  # Another fragmented
        b"\n",  # Completed
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

        # Should yield proper message chunks, not character-by-character
        assert chunks == ["Hello", " world", "!"]
        assert len(chunks) == 3


@pytest.mark.asyncio
async def test_stream_emits_tokens_immediately():
    """Test GLM emits tokens as soon as they're received (character-by-character is correct)."""
    from unittest.mock import AsyncMock, MagicMock, patch

    glm = GLM(api_key="test_key")

    # Mock character-by-character TCP packets - this is desired behavior
    mock_chunks = [
        b"d",
        b"a",
        b"t",
        b"a",
        b":",
        b" ",
        b"{",
        b'"',
        b"c",
        b"h",
        b"o",
        b"i",
        b"c",
        b"e",
        b"s",
        b'"',
        b":",
        b"[",
        b"{",
        b'"',
        b"d",
        b"e",
        b"l",
        b"t",
        b"a",
        b'"',
        b":",
        b"{",
        b'"',
        b"c",
        b"o",
        b"n",
        b"t",
        b"e",
        b"n",
        b"t",
        b'"',
        b":",
        b'"',
        b"H",
        b'"',
        b"}",
        b"}",
        b"]",
        b"}",
        b"\n",
        b"d",
        b"a",
        b"t",
        b"a",
        b":",
        b" ",
        b"{",
        b'"',
        b"c",
        b"h",
        b"o",
        b"i",
        b"c",
        b"e",
        b"s",
        b'"',
        b":",
        b"[",
        b"{",
        b'"',
        b"d",
        b"e",
        b"l",
        b"t",
        b"a",
        b'"',
        b":",
        b"{",
        b'"',
        b"c",
        b"o",
        b"n",
        b"t",
        b"e",
        b"n",
        b"t",
        b'"',
        b":",
        b'"',
        b"i",
        b'"',
        b"}",
        b"}",
        b"]",
        b"}",
        b"\n",
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

        # Should emit tokens as soon as parsed from SSE messages
        # Each complete SSE message yields one content chunk
        assert chunks == ["H", "i"]
        assert len(chunks) == 2
