"""Header widget showing model, session, and mode."""

from rich.text import Text
from textual.widgets import Static


class Header(Static):
    """Header displaying model info, session ID, and mode."""

    def __init__(
        self,
        model_name: str = "GLM",
        session_id: str = "dev_work",
        mode: str = "auto",
        **kwargs,
    ) -> None:
        # Initialize with content immediately
        header_text = Text()
        header_text.append(f"{model_name} ", style="bold cyan")
        header_text.append("• ", style="dim")
        header_text.append(f"session: {session_id} ", style="green")
        header_text.append("• ", style="dim")
        header_text.append(f"{mode} mode", style="yellow")

        super().__init__(header_text, **kwargs)

        self.model_name = model_name
        self.session_id = session_id
        self.mode = mode
        self.styles.height = 1
        self.styles.padding = (0, 1)

    def update_info(
        self, model_name: str | None = None, session_id: str | None = None, mode: str | None = None
    ) -> None:
        """Update header information dynamically."""
        if model_name is not None:
            self.model_name = model_name
        if session_id is not None:
            self.session_id = session_id
        if mode is not None:
            self.mode = mode

        # Re-render the header text
        header_text = Text()
        header_text.append(f"{self.model_name} ", style="bold cyan")
        header_text.append("• ", style="dim")
        header_text.append(f"session: {self.session_id} ", style="green")
        header_text.append("• ", style="dim")
        header_text.append(f"{self.mode} mode", style="yellow")

        self.update(header_text)
