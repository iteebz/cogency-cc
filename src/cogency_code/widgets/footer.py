"""Footer with metrics display and input bar."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Input, Static


class Footer(Horizontal):
    """Footer with metrics and input."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.styles.height = 3
        self.styles.padding = (0, 1)

    def compose(self) -> ComposeResult:
        """Create footer layout."""
        # Metrics with better styling
        metrics_text = Text("0➜0 tokens | 0.0s", style="dim")
        yield Static(metrics_text, id="metrics")

        # Input with cleaner placeholder
        yield Input(
            placeholder="Ask anything...",
            id="input",
            password=False,
        )

        # Config button
        yield Button("⚙︎", id="config-btn", variant="primary")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        value = event.value.strip()
        if value:
            if value.startswith("/"):
                self.post_message(self.SlashCommand(value[1:]))
            else:
                self.post_message(self.QuerySubmitted(value))
            self.query_one("#input", Input).value = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle config button press."""
        if event.button.id == "config-btn":
            # Emit a message to parent to show config
            self.post_message(self.ConfigRequested())

    def update_metrics(self, event) -> None:
        """Update metrics display from cogency event."""
        if event.get("type") == "metrics":
            payload = event.get("payload", {})
            tokens_in = payload.get("tokens_in", 0)
            tokens_out = payload.get("tokens_out", 0)
            duration = payload.get("duration", 0)

            # Create styled metrics text
            metrics_text = Text()
            metrics_text.append(f"{tokens_in}", style="cyan")
            metrics_text.append("➜", style="dim")
            metrics_text.append(f"{tokens_out}", style="green")
            metrics_text.append(" tokens | ", style="dim")
            metrics_text.append(f"{duration:.1f}s", style="yellow")

            self.query_one("#metrics").update(metrics_text)

    class ConfigRequested(Message):
        """Message to request config panel display."""

    class QuerySubmitted(Message):
        """Message emitted when user submits a query."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class SlashCommand(Message):
        """Message emitted when user submits a slash command."""

        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command
