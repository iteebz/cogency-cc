"""Render state machine - explicit state transitions."""

from dataclasses import dataclass, field
from typing import Literal

Phase = Literal["idle", "user", "think", "respond", "call", "result"]


@dataclass
class State:
    """Immutable snapshot of renderer state."""

    phase: Phase = "idle"
    pending_calls: dict = field(default_factory=dict)
    response_started: bool = False
    last_char_newline: bool = True

    def with_phase(self, phase: Phase) -> "State":
        return State(
            phase=phase,
            pending_calls=self.pending_calls.copy(),
            response_started=self.response_started,
            last_char_newline=self.last_char_newline,
        )

    def with_response_started(self, started: bool) -> "State":
        return State(
            phase=self.phase,
            pending_calls=self.pending_calls.copy(),
            response_started=started,
            last_char_newline=self.last_char_newline,
        )

    def with_newline_flag(self, flag: bool) -> "State":
        return State(
            phase=self.phase,
            pending_calls=self.pending_calls.copy(),
            response_started=self.response_started,
            last_char_newline=flag,
        )

    def add_call(self, key: str, call) -> "State":
        new_pending = self.pending_calls.copy()
        new_pending[key] = call
        return State(
            phase=self.phase,
            pending_calls=new_pending,
            response_started=self.response_started,
            last_char_newline=self.last_char_newline,
        )

    def pop_call(self) -> tuple["State", tuple | None]:
        if not self.pending_calls:
            return self, None
        key = list(self.pending_calls.keys())[-1]
        call = self.pending_calls[key]
        new_pending = self.pending_calls.copy()
        del new_pending[key]
        new_state = State(
            phase=self.phase,
            pending_calls=new_pending,
            response_started=self.response_started,
            last_char_newline=self.last_char_newline,
        )
        return new_state, (key, call)

    def clear_calls(self) -> "State":
        return State(
            phase=self.phase,
            pending_calls={},
            response_started=self.response_started,
            last_char_newline=self.last_char_newline,
        )

    def reset_turn(self) -> "State":
        return self.with_response_started(False)
