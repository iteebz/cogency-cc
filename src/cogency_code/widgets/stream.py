"""Event rendering widget for cogency-code."""

import pyperclip
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from cogency_code.events import render_event


class StreamView(VerticalScroll):
    """Widget that displays cogency agent events using cogency's formatting."""

    BINDINGS = [
        Binding("ctrl+c", "copy_selection", "Copy", show=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.active_streams = {}
        self.last_event_type = None
        self.last_call_content = None

    async def add_event(self, event) -> None:
        """Add a cogency event using the centralized event renderer."""
        event_type = event["type"]
        payload = event.get("payload", {})

        if event_type == "metrics":
            return

        if event_type == "user":
            self.active_streams = {}
            self.last_call_content = None
            rendered = render_event(event)
            if rendered:
                await self.mount(Static(rendered))
            self.last_event_type = event_type
        elif event_type in ("think", "respond"):
            if event_type not in self.active_streams:
                prefix = "\n>" if event_type == "respond" else "\n~"
                widget = Static(prefix)
                await self.mount(widget)
                self.active_streams[event_type] = {"widget": widget, "buffer": prefix}

            stream = self.active_streams[event_type]
            stream["buffer"] += event["content"]
            stream["widget"].update(stream["buffer"])
            self.scroll_end(animate=False)

            if payload.get("done", False):
                del self.active_streams[event_type]
                self.last_event_type = event_type
        elif event_type == "call":
            if event["content"] == self.last_call_content:
                return
            self.last_call_content = event["content"]
            self.active_streams = {}
            rendered = render_event(event)
            if rendered:
                await self.mount(Static(rendered))
            self.last_event_type = None
        elif event_type == "result":
            self.active_streams = {}
            rendered = render_event(event)
            if rendered:
                await self.mount(Static(rendered))
            self.last_event_type = "result"
        else:
            rendered = render_event(event)
            if rendered:
                await self.mount(Static(rendered))
            self.last_event_type = event_type

    def clear(self) -> None:
        """Clear the stream view."""
        self.remove_children()
        self.active_streams = {}
        self.last_event_type = None
        self.last_call_content = None

    def action_copy_selection(self) -> None:
        """Copy last visible text content to clipboard."""
        try:
            content = self._get_last_content()
            if content:
                pyperclip.copy(content)
                self.app.notify("Copied to clipboard")
        except Exception:
            self.app.notify("Failed to copy to clipboard", severity="error")

    def _get_last_content(self) -> str:
        """Extract text content from the last visible widget."""
        try:
            # Try to get children from the actual widget structure
            try:
                children = list(self.children)
            except Exception:
                # Fallback for testing when widget isn't mounted
                children = list(getattr(self, "_nodes", []))

            if not children:
                return ""

            # Get the last Static widget that has content
            for widget in reversed(children):
                if hasattr(widget, "content"):
                    content = widget.content
                    if isinstance(content, str):
                        return content
                    if hasattr(content, "plain"):
                        return content.plain
                    if hasattr(content, "text"):
                        return content.text
                    if hasattr(content, "__str__"):
                        return str(content)
                elif hasattr(widget, "renderable") and widget.renderable:
                    if hasattr(widget.renderable, "plain"):
                        return widget.renderable.plain
                    if hasattr(widget.renderable, "text"):
                        return widget.renderable.text
                    if isinstance(widget.renderable, str):
                        return widget.renderable
                    if hasattr(widget.renderable, "__str__"):
                        return str(widget.renderable)
                elif hasattr(widget, "text"):
                    return widget.text
                elif hasattr(widget, "_text"):
                    return widget._text

            return ""
        except Exception:
            return ""
