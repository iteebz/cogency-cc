from unittest.mock import MagicMock

from cc.render.color import C  # Import C for ANSI codes
from cc.render.format import format_call, format_result, tool_name


class MockCall(MagicMock):
    def __init__(self, name, args):
        super().__init__()
        self.name = name
        self.args = args


def test_tool_name_simple():
    assert tool_name("read") == "read"


def test_tool_name_dotted():
    assert tool_name("code.read") == "read"


def test_format_call_no_args():
    call = MockCall("read", {})
    # Expect bolded output
    assert format_call(call) == f"{C.BOLD}read{C.R}(): ..."


def test_format_call_with_args():
    call = MockCall("code.read", {"file": "test.py"})
    # Expect bolded output
    assert format_call(call) == f"{C.BOLD}read{C.R}(test.py): ..."


def test_format_result():
    call = MockCall("code.read", {"file": "test.py"})
    payload = {"outcome": "Read test.py (10 lines)"}
    # Expect bolded output for the tool name
    assert format_result(call, payload) == f"{C.BOLD}read{C.R}(test.py): 10 lines"


# ... (rest of the tests remain unchanged)
