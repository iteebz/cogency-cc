"""Tests for render.format pure functions."""

from cc.render.format import (
    format_call,
    format_result,
    tool_arg,
    tool_name,
    tool_outcome,
)


def test_tool_name_simple():
    assert tool_name("read") == "read"


def test_tool_name_dotted():
    assert tool_name("code.read") == "read"
    assert tool_name("memory.recall") == "recall"


def test_tool_arg_file():
    assert tool_arg({"file": "test.py"}) == "test.py"


def test_tool_arg_truncate():
    long_path = "a" * 60
    assert tool_arg({"file": long_path}) == "a" * 47 + "..."


def test_tool_arg_priority():
    assert tool_arg({"file": "a.py", "other": "b"}) == "a.py"
    assert tool_arg({"path": "x", "other": "y"}) == "x"


def test_tool_arg_fallback():
    assert tool_arg({"unknown": "val"}) == "val"


def test_tool_arg_empty():
    assert tool_arg({}) == ""
    assert tool_arg(None) == ""


def test_tool_outcome_error():
    assert tool_outcome({"error": True, "outcome": "failed"}) == "failed"


def test_tool_outcome_read():
    assert tool_outcome({"outcome": "Read test.py (42 lines)"}) == "+42 lines"


def test_tool_outcome_edit():
    assert tool_outcome({"outcome": "Edited test.py (+5/-2)"}) == "+5/-2"


def test_tool_outcome_ls():
    assert tool_outcome({"outcome": "Listed 10 items"}) == "10 items"


def test_tool_outcome_grep():
    assert tool_outcome({"outcome": "Found 3 matches"}) == "3 matches"


def test_tool_outcome_ok():
    assert tool_outcome({"outcome": ""}) == "ok"
    assert tool_outcome({}) == "ok"


def test_tool_outcome_passthrough():
    assert tool_outcome({"outcome": "custom result"}) == "custom result"


class MockCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


def test_format_call_no_args():
    call = MockCall("read", {})
    assert format_call(call) == "read(): ..."


def test_format_call_with_args():
    call = MockCall("code.read", {"file": "test.py"})
    assert format_call(call) == "read(test.py): ..."


def test_format_result():
    call = MockCall("code.read", {"file": "test.py"})
    payload = {"outcome": "Read test.py (10 lines)"}
    assert format_result(call, payload) == "read(test.py): +10 lines"
