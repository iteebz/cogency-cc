import asyncio
import contextlib
import inspect

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import Key

from cogency_code.agent import create_agent
from cogency_code.commands import dispatch
from cogency_code.state import Config
from cogency_code.widgets.config import ConfigPanel
from cogency_code.widgets.footer import Footer
from cogency_code.widgets.header import Header
from cogency_code.widgets.resume import ResumeConversation
from cogency_code.widgets.stream import StreamView


class CogencyCode(App):
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
        height: auto;
        padding: 1;
    }

    #exit-hint {
        dock: bottom;
        height: 1;
        color: $text-muted;
        text-align: right;
        padding-right: 2;
    }

    #input {
        height: 1;
        border: none;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+g", "toggle_config", "Config"),
        Binding("escape", "cancel_request", "Cancel", show=False),
    ]

    def __init__(
        self,
        llm_provider: str = None,
        mode: str = "auto",
        **kwargs,
    ) -> None:
        import uuid

        super().__init__(**kwargs)

        self.config = Config()
        if llm_provider:
            self.config.provider = llm_provider
        self.llm_provider = self.config.provider
        self.conversation_id = str(uuid.uuid4())
        preferred_user_id = kwargs.pop("user_id", None)
        if preferred_user_id is None and mode == "resume":
            preferred_user_id = "custom_user"
        self.user_id = preferred_user_id or "cogency"
        self.mode = mode or self.config.mode
        self.current_task = None
        self.exit_hint_timer = None
        self.exit_hint_visible = False

        # Initialize agent using factory
        self.agent = create_agent(self.config)

    def compose(self) -> ComposeResult:
        yield Header(
            model_name=self.llm_provider.upper(), session_id=self.conversation_id, mode=self.mode
        )
        yield StreamView()
        yield Footer()

    def on_mount(self) -> None:
        self.stream_view = self.query_one(StreamView)
        self.footer = self.query_one(Footer)
        self.header = self.query_one(Header)
        self.title = "cogency-code"

        input_widget = self.query_one("#input")
        input_widget.focus()

        # If in resume selection mode, show conversation picker
        if self.mode == "resume_selection":
            self.push_screen(ResumeConversation(), self._conversation_selected)

    async def _conversation_selected(self, session_id: str | None) -> None:
        if session_id:
            from cogency.lib.storage import default_storage

            self.conversation_id = session_id
            self.mode = "replay"

            if hasattr(self, "header"):
                self.header.update_info(
                    model_name=self.llm_provider.upper(),
                    session_id=self.conversation_id,
                    mode=self.mode,
                )

            storage = default_storage()
            messages = await storage.load_messages(
                conversation_id=session_id, user_id=self.user_id, exclude=["metrics", "chunk"]
            )

            for msg in messages:
                await self.stream_view.add_event(msg)
        else:
            await self.stream_view.add_event(
                {
                    "type": "respond",
                    "content": "No session selected. Starting new session.",
                    "payload": {},
                    "timestamp": 0,
                }
            )

    async def on_footer_slash_command(self, event) -> None:
        result = await dispatch(event.command, self)
        if result:
            await self.stream_view.add_event(result)

    async def on_footer_query_submitted(self, event) -> None:
        if self.current_task:
            self.current_task.cancel()
        self.current_task = self.run_worker(self.handle_query(event.query))
        input_widget = self.query_one("#input")
        input_widget.focus()

    async def handle_query(self, query: str) -> None:
        try:
            last_metrics = None
            async for event in self.agent(
                query,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                chunks=True,
            ):
                if event["type"] == "metrics":
                    last_metrics = event
                else:
                    if hasattr(self, "stream_view"):
                        await self.stream_view.add_event(event)

            if last_metrics and hasattr(self, "header"):
                self.header.update_metrics(last_metrics)

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError) and hasattr(self, "stream_view"):
                await self.stream_view.add_event(
                    {
                        "type": "error",
                        "content": f"Error: {str(e)}",
                        "payload": {},
                        "timestamp": 0,
                    }
                )
        finally:
            self.current_task = None

    async def on_unmount(self) -> None:
        await self._cleanup_llm()

    async def _cleanup_llm(self) -> None:
        if hasattr(self.agent, "config") and hasattr(self.agent.config, "llm"):
            llm = self.agent.config.llm
            if llm and hasattr(llm, "close"):
                with contextlib.suppress(Exception):
                    await llm.close()

    async def on_key(self, event: Key) -> None:
        if event.key == "ctrl+c":
            # Check if focus is on StreamView - if so, let it handle copy
            focused = self.focused
            if focused and isinstance(focused, StreamView):
                return  # Let StreamView handle the copy
            event.prevent_default()
            if self.exit_hint_visible:
                self.exit()
            else:
                input_widget = self.query_one("#input")
                input_widget.clear()
                await self._show_exit_hint()

    def action_cancel_request(self) -> None:
        if self.current_task:
            self.current_task.cancel()

    def action_clear(self) -> None:
        self.stream_view.clear()

    def action_toggle_config(self) -> None:
        self.push_screen(ConfigPanel(), self._config_updated)

    async def _show_exit_hint(self) -> None:
        from textual.widgets import Label

        if self.exit_hint_timer:
            self.exit_hint_timer.stop()

        try:
            hint = self.query_one("#exit-hint")
            hint.update("Ctrl-C again to exit")
        except Exception:
            hint = Label("Ctrl-C again to exit", id="exit-hint")
            await self.mount(hint)

        self.exit_hint_visible = True

        def hide_hint():
            hint.update("")
            self.exit_hint_visible = False

        self.exit_hint_timer = self.set_timer(1.0, hide_hint)

    async def _config_updated(self, config_data: dict) -> None:
        if not isinstance(config_data, dict):
            if hasattr(self, "push_screen"):
                result = self.push_screen(ConfigPanel(), self._config_updated)
                if inspect.isawaitable(result):
                    await result
            return

        if config_data:
            new_provider = config_data.get("provider")
            agent_needs_recreation = False

            if new_provider and new_provider != self.config.provider:
                self.config.provider = new_provider
                self.llm_provider = new_provider
                agent_needs_recreation = True

            new_identity = config_data.get("identity")
            if new_identity and new_identity != self.config.identity:
                self.config.identity = new_identity
                agent_needs_recreation = True

            # Recreate agent if provider or identity changed
            if agent_needs_recreation:
                self.agent = create_agent(self.config)

            new_mode = config_data.get("mode")
            if new_mode:
                self.mode = new_mode

            # Save all config changes
            self.config.save()

            if hasattr(self, "header"):
                self.header.update_info(
                    model_name=self.llm_provider.upper(),
                    session_id=self.conversation_id,
                    mode=self.mode,
                )

            if hasattr(self, "stream_view"):
                await self.stream_view.add_event(
                    {
                        "type": "respond",
                        "content": f"Configuration updated: LLM={self.llm_provider}, mode={self.mode}, identity={self.config.identity}",
                        "payload": {},
                        "timestamp": 0,
                    }
                )


if __name__ == "__main__":
    app = CogencyCode()
    app.run()
