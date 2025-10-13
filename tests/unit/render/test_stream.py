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
        await renderer._render_event(tool_call_event)

        # Simulate a tool result event
        tool_result_event = {
            "type": "result",
            "payload": {"outcome": "121 items", "content": "file1.txt\nfile2.txt"},
        }
        await renderer._render_event(tool_result_event)

        output = captured_output.getvalue()

        # Construct the expected result line with ANSI codes
        dummy_call = ToolCall(name="ls", args={"path": "."})
        formatted_result_text = format_result(dummy_call, tool_result_event["payload"])

        expected_result_line = f"\r\033[K{C.GREEN}●{C.R} {formatted_result_text}"

        assert expected_result_line in output, f"Expected result line not found in output: {output}"

    finally:
        sys.stdout = sys.__stdout__  # Restore stdout
