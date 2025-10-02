"""Main Textual app for cogency-code."""

from cogency.core.agent import Agent
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI
from textual.app import App, ComposeResult
from textual.binding import Binding

from cogency_code.llms.glm import GLM
from cogency_code.state import Config
from cogency_code.widgets.config import ConfigPanel
from cogency_code.widgets.footer import Footer
from cogency_code.widgets.header import Header
from cogency_code.widgets.stream import StreamView


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
        conversation_id: str = "dev_work",
        user_id: str = "cogency_user",
        mode: str = "auto",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.config = Config()
        self.llm_provider = llm_provider or self.config.llm
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.mode = mode or self.config.mode

        # Initialize LLM provider
        self.llm = self._create_llm(self.llm_provider)

        # Initialize agent with project access (default)
        self.agent = Agent(llm=self.llm, mode="replay", max_iterations=3, debug=True, base_dir=".")

    def _create_llm(self, provider_name: str):
        """Create LLM provider instance with API key."""
        providers = {
            "glm": GLM,
            "openai": OpenAI,
            "anthropic": Anthropic,
            "gemini": Gemini,
        }

        if provider_name not in providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Get API key from config or environment
        api_key = self.config.get_api_key(provider_name)

        return providers[provider_name](api_key=api_key)

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
            new_provider = config_data.get("llm_provider")
            if new_provider and new_provider != self.llm_provider:
                self.llm_provider = new_provider
                self.llm = self._create_llm(new_provider)
                self.agent = Agent(llm=self.llm)

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
