"""Header widget showing model, session, mode, and metrics."""

from rich.text import Text
from textual.widgets import Static


class Header(Static):
    """Header displaying model info, session ID, mode, and metrics."""

    def __init__(
        self,
        model_name: str = "GLM",
        session_id: str = "dev_work",
        mode: str = "auto",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.model_name = model_name
        self.session_id = session_id
        self.mode = mode
        self.metrics = "0→0 | 0.0s"
        self.styles.height = 1
        self.styles.padding = (0, 1)
        self._render()

    def _render(self) -> None:
        txt = Text()
        txt.append(f"{self.model_name} ", style="bold cyan")
        txt.append("• ", style="dim")
        txt.append(f"{self.session_id[:8]} ", style="green")
        txt.append("• ", style="dim")
        txt.append(f"{self.mode} ", style="yellow")
        txt.append("• ", style="dim")
        txt.append(self.metrics, style="dim")
        self.update(txt)

    def update_info(
        self, model_name: str | None = None, session_id: str | None = None, mode: str | None = None
    ) -> None:
        if model_name is not None:
            self.model_name = model_name
        if session_id is not None:
            self.session_id = session_id
        if mode is not None:
            self.mode = mode
        self._render()

    def update_metrics(self, event) -> None:
        if event.get("type") == "metrics":
            p = event.get("payload", {})
            tin = p.get("tokens_in", 0)
            tout = p.get("tokens_out", 0)
            dur = p.get("duration", 0)
            self.metrics = f"{tin}→{tout} | {dur:.1f}s"
            self._render()
