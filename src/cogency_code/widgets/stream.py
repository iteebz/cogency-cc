"""Event rendering widget for cogency-code."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog

from cogency_code.events import render_event


class StreamView(Vertical):
    """Widget that displays cogency agent events using cogency's formatting."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.styles.padding = (0, 0)

    def compose(self) -> ComposeResult:
        yield RichLog(wrap=True, markup=True, auto_scroll=True, highlight=True, id="event-log", max_lines=10000)

    async def add_event(self, event) -> None:
        """Add a cogency event using the centralized event renderer."""
        rendered = render_event(event)
        if rendered:
            log = self.query_one("#event-log", RichLog)
            log.write(rendered)

    def clear(self) -> None:
        """Clear the stream view."""
        log = self.query_one("#event-log", RichLog)
        log.clear()
