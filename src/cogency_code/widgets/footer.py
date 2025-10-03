"""Footer with auto-expanding input."""

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Input, Static


class Footer(Static):
    """Footer with minimal auto-expanding input."""

    def compose(self) -> ComposeResult:
        yield Input(id="input", placeholder="Enter query or /command")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if value:
            if value.startswith("/"):
                self.post_message(self.SlashCommand(value[1:]))
            else:
                self.post_message(self.QuerySubmitted(value))
        event.input.clear()

    class QuerySubmitted(Message):
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class SlashCommand(Message):
        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command
