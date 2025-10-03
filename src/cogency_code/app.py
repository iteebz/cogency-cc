"""Main Textual app for cogency-code."""

from textual.app import App, ComposeResult
from textual.binding import Binding

from cogency_code.agent import create_agent
from cogency_code.commands import dispatch
from cogency_code.widgets.resume import ResumeConversation
from cogency_code.widgets.config import ConfigPanel
from cogency_code.widgets.footer import Footer
from cogency_code.widgets.header import Header
from cogency_code.widgets.stream import StreamView
from cogency_code.state import Config


class CogencyCode(App):
    """Main TUI application for cogency-code."""

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }

    Header {
        background: $surface;
        color: $primary;
        text-align: center;
        padding: 0 1;
        height: 1;
        border-bottom: solid $accent;
    }

    StreamView {
        height: 1fr;
        background: $background;
        border: none;
        padding: 1 2;
    }

    Footer {
        background: $surface;
        height: 3;
        padding: 0 1;
        border-top: solid $accent;
    }

    #metrics {
        width: 35%;
        text-align: left;
        color: $text-muted;
    }

    #input {
        width: 55%;
    }

    #config-btn {
        width: 10%;
        min-width: 3;
    }

    #header-text {
        color: $primary;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+g", "toggle_config", "Config"),
    ]

    def __init__(
        self,
        llm_provider: str = "glm",
        mode: str = "auto",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.config = Config()
        self.llm_provider = llm_provider or self.config.llm
        self.conversation_id = "dev_work"
        self.user_id = "cogency"  # Fixed single user
        self.mode = mode or self.config.mode

        # Initialize agent using factory
        self.agent = create_agent(self.config)

    def compose(self) -> ComposeResult:
        """Create the app layout."""
        yield Header(
            model_name=self.llm_provider.upper(), session_id=self.conversation_id, mode=self.mode
        )
        yield StreamView()
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        self.stream_view = self.query_one(StreamView)
        self.footer = self.query_one(Footer)
        self.header = self.query_one(Header)
        self.title = "cogency-code"
        
        # If in resume selection mode, show conversation picker
        if self.mode == "resume_selection":
            self.push_screen(ResumeConversation(), self._conversation_selected)

    async def _conversation_selected(self, session_id: str | None) -> None:
        """Handle session selection from resume screen."""
        if session_id:
            # Update the app with the selected session
            self.conversation_id = session_id
            self.mode = "replay"  # Switch to replay mode for resumed session
            
            # Update header to show the selected session
            self.header.update_info(
                model_name=self.llm_provider.upper(),
                session_id=self.conversation_id,
                mode=self.mode,
            )
            
            # Add notification to stream
            await self.stream_view.add_event({
                "type": "respond",
                "content": f"Resumed session: {session_id}",
                "payload": {},
                "timestamp": 0,
            })
        else:
            # No selection made - exit
            await self.stream_view.add_event({
                "type": "respond", 
                "content": "No session selected. Starting new session.",
                "payload": {},
                "timestamp": 0,
            })

    async def on_footer_slash_command(self, event) -> None:
        """Handle slash commands from footer."""
        result = await dispatch(event.command, self)
        if result:
            await self.stream_view.add_event(result)

    async def on_footer_query_submitted(self, event) -> None:
        """Handle query submission from footer."""
        await self.stream_view.add_event({
            "type": "user",
            "content": event.query,
            "timestamp": 0,
        })
        await self.handle_query(event.query)

    async def handle_query(self, query: str) -> None:
        """Handle user input - stream agent response."""
        try:
            async for event in self.agent(
                query,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                chunks=False,  # Semantic mode
            ):
                await self.stream_view.add_event(event)

                if event["type"] == "metrics":
                    self.footer.update_metrics(event)

        except Exception as e:
            await self.stream_view.add_event(
                {
                    "type": "error",
                    "content": f"Error: {str(e)}",
                    "payload": {},
                    "timestamp": 0,
                }
            )

    def action_clear(self) -> None:
        """Clear the stream view."""
        self.stream_view.clear()

    def action_toggle_config(self) -> None:
        """Toggle configuration panel."""
        self.push_screen(ConfigPanel(), self._config_updated)

    async def on_footer_config_requested(self, event) -> None:
        """Handle config request from footer."""
        await self.push_screen(ConfigPanel(), self._config_updated)

    async def _config_updated(self, config_data: dict) -> None:
        """Handle configuration updates."""
        if config_data:
            new_provider = config_data.get("provider")
            if new_provider and new_provider != self.config.provider:
                self.config.provider = new_provider
                self.llm_provider = new_provider
                self.agent = create_agent(self.config)  # Recreate with new config

            new_mode = config_data.get("mode")
            if new_mode:
                self.mode = new_mode

            self.header.update_info(
                model_name=self.llm_provider.upper(),
                session_id=self.conversation_id,
                mode=self.mode,
            )

            await self.stream_view.add_event(
                {
                    "type": "respond",
                    "content": f"Configuration updated: LLM={self.llm_provider}, mode={self.mode}",
                    "payload": {},
                    "timestamp": 0,
                }
            )


if __name__ == "__main__":
    app = CogencyCode()
    app.run()
