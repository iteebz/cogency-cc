import io
import sys

import pytest
from cogency.core.protocols import ToolCall

from cc.render import Renderer
from cc.render.color import C
from cc.render.format import format_result


@pytest.mark.asyncio
async def test_renderer_clears_line_before_tool_result():
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        renderer = Renderer()

        # Simulate a tool call event to start a spinner
        tool_call_event = {"type": "call", "content": '{"name": "ls", "args": {"path": "."}}'}
        await renderer._dispatch(tool_call_event)

        # Simulate a tool result event
        tool_result_event = {
            "type": "result",
            "payload": {"outcome": "121 items", "content": "file1.txt\nfile2.txt"},
        }
        await renderer._dispatch(tool_result_event)

        output = captured_output.getvalue()

        # Construct the expected result line with ANSI codes
        dummy_call = ToolCall(name="ls", args={"path": "."})
        formatted_result_text = format_result(dummy_call, tool_result_event["payload"])

        expected_result_line = f"\r\033[K{C.GREEN}●{C.R} {formatted_result_text}"

        assert expected_result_line in output, f"Expected result line not found in output: {output}"

    finally:
        sys.stdout = sys.__stdout__


@pytest.mark.asyncio
async def test_think_event_renders_with_grey_tilde():
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        renderer = Renderer()

        think_event = {"type": "think", "content": "reasoning about the problem"}
        await renderer._dispatch(think_event)

        output = captured_output.getvalue()

        assert f"{C.GRAY}~{C.R} " in output
        assert f"{C.GRAY}reasoning about the problem{C.R}" in output

    finally:
        sys.stdout = sys.__stdout__


@pytest.mark.asyncio
async def test_renderer_displays_total_token_count_in_header():
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        # Mock Config and latest_metric
        class MockConfig:
            model = "test-model"
            provider = "test-provider"

        mock_config = MockConfig()

        renderer = Renderer(
            config=mock_config,
            latest_metric=None,  # Simulate no latest_metric
            messages=[{"type": "user", "content": "hello"}],  # Add a message to avoid 0 msgs
        )

        # Call _render_header directly
        renderer._render_header()

        output = captured_output.getvalue()

        # Expected token count: 0.0k tokens when no latest_metric
        expected_token_string = "0.0k tokens"
        assert expected_token_string in output, (
            f"Expected token count not found in header: {output}"
        )

    finally:
        sys.stdout = sys.__stdout__
