"""Test GLM intelligent §end injection on [DONE] event."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc.llms.glm import GLM


@pytest.mark.asyncio
async def test_glm_injects_section_on_done():
    """Test that GLM yields §end when [DONE] SSE event is received and no pending tool calls."""

    glm = GLM(api_key="test_key")

    # Create a mock response context manager
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content = AsyncMock()

    # Mock the content iterator to yield SSE chunks without tool calls
    async def mock_iter_any():
        yield b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        yield b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
        yield b"data: [DONE]\n\n"

    mock_response.content.iter_any = mock_iter_any

    # Create a mock session that returns our mock response
    mock_session = AsyncMock()
    mock_session.post = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch.object(glm, "_create_session", return_value=mock_session):
        # Collect all yielded chunks
        chunks = []
        async for chunk in glm.stream([{"role": "user", "content": "test"}]):
            chunks.append(chunk)

        # Verify that §end is yielded as the final chunk when no pending tool calls
        assert chunks[-1] == "§end"
        # Verify that normal content is still yielded
        assert any("Hello" in chunk for chunk in chunks[:-1])
        assert any(" world" in chunk for chunk in chunks[:-1])


@pytest.mark.asyncio
async def test_glm_no_section_when_tool_call_pending():
    """Test that GLM doesn't inject §end when there's a pending tool call."""

    glm = GLM(api_key="test_key")

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content = AsyncMock()

    # Mock content with a tool call but no execute - should not inject §end
    async def mock_iter_any():
        yield b'data: {"choices":[{"delta":{"content":"\\u00a7call: "}}]}\n\n'
        yield b'data: {"choices":[{"delta":{"content":"{\\"name\\": \\"ls\\", \\"args\\": {\\"path\\": \\".\\"}}"}]}]\n\n'
        yield b"data: [DONE]\n\n"

    mock_response.content.iter_any = mock_iter_any

    mock_session = AsyncMock()
    mock_session.post = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch.object(glm, "_create_session", return_value=mock_session):
        chunks = []
        async for chunk in glm.stream([{"role": "user", "content": "test"}]):
            chunks.append(chunk)

        # Should not contain §end when there's a pending tool call
        assert "§end" not in chunks
        # Should still yield the tool call content
        assert any("§call:" in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_glm_injects_section_when_tool_complete():
    """Test that GLM injects §end when tool call is followed by execute."""

    glm = GLM(api_key="test_key")

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content = AsyncMock()

    # Mock content with complete tool call (call + execute)
    async def mock_iter_any():
        yield b'data: {"choices":[{"delta":{"content":"\\u00a7call: "}}]}\n\n'
        yield b'data: {"choices":[{"delta":{"content":"{\\"name\\": \\"ls\\", \\"args\\": {\\"path\\": \\".\\"}}"}]}]\n\n'
        yield b'data: {"choices":[{"delta":{"content":"\\n\\u00a7execute"}}]}\n\n'
        yield b"data: [DONE]\n\n"

    mock_response.content.iter_any = mock_iter_any

    mock_session = AsyncMock()
    mock_session.post = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch.object(glm, "_create_session", return_value=mock_session):
        chunks = []
        async for chunk in glm.stream([{"role": "user", "content": "test"}]):
            chunks.append(chunk)

        # Should contain §end when tool call is complete
        assert "§end" in chunks
        # Should still yield the tool call content
        assert any("§call:" in chunk for chunk in chunks)
        assert any("§execute" in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_glm_should_inject_end_logic():
    """Test the _should_inject_end method directly."""

    glm = GLM(api_key="test_key")

    # Case 1: No tool calls - should inject
    glm._recent_content = ["Hello world", "How are you?"]
    assert glm._should_inject_end() is True

    # Case 2: Tool call without execute - should NOT inject
    glm._recent_content = ["§call: ", '{"name": "ls", "args": {"path": "."}}']
    assert glm._should_inject_end() is False

    # Case 3: Complete tool call (call + execute) - should inject
    glm._recent_content = ["§call: ", '{"name": "ls"}', "\n§execute"]
    assert glm._should_inject_end() is True

    # Case 4: Multiple tool calls, last one complete - should inject
    glm._recent_content = [
        "§call: ",
        '{"name": "ls1"}',
        "\n§execute",
        "§call: ",
        '{"name": "ls2"}',
        "\n§execute",
    ]
    assert glm._should_inject_end() is True

    # Case 5: Multiple tool calls, last one pending - should NOT inject
    glm._recent_content = ["§call: ", '{"name": "ls1"}', "\n§execute", "§call: ", '{"name": "ls2"}']
    assert glm._should_inject_end() is False
