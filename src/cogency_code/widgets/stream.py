"""Event rendering widget for cogency-code."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from cogency_code.events import render_event


class StreamView(VerticalScroll):
    """Widget that displays cogency agent events using cogency's formatting."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.active_streams = {}

    async def add_event(self, event) -> None:
        """Add a cogency event using the centralized event renderer."""
        event_type = event["type"]
        payload = event.get("payload", {})
        
        if event_type == "user":
            self.active_streams = {}
            rendered = render_event(event)
            if rendered:
                await self.mount(Static(rendered))
        elif event_type in ("think", "respond"):
            if event_type not in self.active_streams:
                prefix = ">" if event_type == "respond" else "~"
                widget = Static(prefix)
                await self.mount(widget)
                self.active_streams[event_type] = {"widget": widget, "buffer": prefix}
            
            stream = self.active_streams[event_type]
            stream["buffer"] += event["content"]
            stream["widget"].update(stream["buffer"])
            
            if payload.get("done", False):
                del self.active_streams[event_type]
        else:
            rendered = render_event(event)
            if rendered:
                widget = Static(rendered)
                await self.mount(widget)

    def clear(self) -> None:
        """Clear the stream view."""
        self.remove_children()
        self.active_streams = {}
