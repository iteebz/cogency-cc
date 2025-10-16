"""Lightweight state machine transition tests."""

from cc.render.state import State


def test_init_state():
    s = State()
    assert s.phase == "idle"
    assert s.pending_calls == {}
    assert s.response_started is False
    assert s.last_char_newline is True


def test_phase_transition():
    s = State()
    s = s.with_phase("user")
    assert s.phase == "user"
    s = s.with_phase("think")
    assert s.phase == "think"


def test_response_started_flag():
    s = State()
    s = s.with_response_started(True)
    assert s.response_started is True
    s = s.with_response_started(False)
    assert s.response_started is False


def test_newline_flag():
    s = State()
    assert s.last_char_newline is True
    s = s.with_newline_flag(False)
    assert s.last_char_newline is False
    s = s.with_newline_flag(True)
    assert s.last_char_newline is True


def test_add_call_maintains_state():
    s = State(phase="call", response_started=True, last_char_newline=False)
    s = s.add_call("test_key", {"name": "foo"})
    assert s.phase == "call"
    assert s.response_started is True
    assert s.last_char_newline is False
    assert "test_key" in s.pending_calls


def test_pop_call_stack_lifo():
    s = State()
    s = s.add_call("first", {"name": "a"})
    s = s.add_call("second", {"name": "b"})
    s, (key, call) = s.pop_call()
    assert key == "second"
    assert call["name"] == "b"
    assert len(s.pending_calls) == 1


def test_pop_call_empty_returns_none():
    s = State()
    new_s, result = s.pop_call()
    assert new_s is s
    assert result is None


def test_clear_calls():
    s = State()
    s = s.add_call("a", {}).add_call("b", {})
    s = s.clear_calls()
    assert s.pending_calls == {}


def test_user_think_respond_path():
    s = State()
    s = s.reset_turn()
    s = s.with_phase("user")
    assert s.response_started is False
    s = s.with_phase("think")
    s = s.with_newline_flag(True)
    s = s.with_phase("respond").with_response_started(True)
    assert s.phase == "respond"
    assert s.response_started is True
    assert s.last_char_newline is True


def test_user_think_call_result_path():
    s = State()
    s = s.reset_turn()
    s = s.with_phase("user")
    s = s.with_phase("think")
    s = s.with_newline_flag(True)
    s = s.with_phase("call")
    s = s.add_call("key1", {"name": "read", "args": {"path": "test.py"}})
    assert "key1" in s.pending_calls
    s = s.with_phase("result")
    s, popped = s.pop_call()
    assert popped is not None
    assert popped[0] == "key1"


def test_state_immutability():
    s1 = State()
    s2 = s1.with_phase("user")
    assert s1.phase == "idle"
    assert s2.phase == "user"


def test_transitions_preserve_other_fields():
    s = State()
    s = s.with_phase("respond").with_response_started(True).with_newline_flag(False)
    s = s.add_call("key", {})
    s = s.with_phase("result")
    assert s.response_started is True
    assert s.last_char_newline is False
    assert "key" in s.pending_calls
