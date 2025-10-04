"""Configuration panel for runtime settings."""

import os

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static


class ConfigPanel(ModalScreen):
    """Modal configuration panel for API keys and settings."""

    BINDINGS = [
        ("escape,q", "app.pop_screen", "Close"),
        ("ctrl+c", "app.pop_screen", "Close"),
    ]

    CSS = """
    ConfigPanel {
        align: center middle;
        background: $surface 80%;
        border: thick $primary;
        width: 60%;
        height: 70%;
        padding: 1;
    }

    .config-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }

    .config-section {
        margin: 1 0;
        padding: 1;
        border: solid $accent;
        background: $background;
    }

    .config-row {
        height: auto;
        margin: 0 0 1 0;
    }

    .config-buttons {
        align: center middle;
        height: 3;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        """Create config panel layout."""
        yield Static("Configuration", classes="config-title")

        # API Keys Section
        with Vertical(classes="config-section"):
            yield Label("API Keys", classes="config-title")
            with Horizontal(classes="config-row"):
                yield Label("GLM API Key:", width=15)
                yield Input(
                    placeholder="Enter GLM API key...",
                    password=True,
                    id="glm-key",
                    value=os.getenv("GLM_API_KEY", ""),
                )
            with Horizontal(classes="config-row"):
                yield Label("OpenAI Key:", width=15)
                yield Input(
                    placeholder="Enter OpenAI API key...",
                    password=True,
                    id="openai-key",
                    value=os.getenv("OPENAI_API_KEY", ""),
                )
            with Horizontal(classes="config-row"):
                yield Label("Anthropic Key:", width=15)
                yield Input(
                    placeholder="Enter Anthropic API key...",
                    password=True,
                    id="anthropic-key",
                    value=os.getenv("ANTHROPIC_API_KEY", ""),
                )

        # Settings Section
        with Vertical(classes="config-section"):
            yield Label("Settings", classes="config-title")
            with Horizontal(classes="config-row"):
                yield Label("LLM Provider:", width=15)
                yield Select(
                    options=[
                        ("GLM", "glm"),
                        ("OpenAI", "openai"),
                        ("Anthropic", "anthropic"),
                        ("Gemini", "gemini"),
                    ],
                    value="glm",
                    id="llm-select",
                )
            with Horizontal(classes="config-row"):
                yield Label("Mode:", width=15)
                yield Select(
                    options=[
                        ("Auto", "auto"),
                        ("Resume", "resume"),
                        ("Replay", "replay"),
                    ],
                    value="auto",
                    id="mode-select",
                )
            with Horizontal(classes="config-row"):
                yield Label("Identity:", width=15)
                yield Select(
                    options=[
                        ("Coding", "coding"),
                        ("Cothinker", "cothinker"),
                        ("Assistant", "assistant"),
                    ],
                    value="coding",
                    id="identity-select",
                )

        # Buttons
        with Horizontal(classes="config-buttons"):
            yield Button("Save", variant="success", id="save-btn")
            yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            config_data = self.save_config()
            self.dismiss(config_data)
        else:
            self.dismiss(None)

    def save_config(self) -> dict:
        """Save configuration to environment and return config data."""
        glm_key = self.query_one("#glm-key", Input).value
        openai_key = self.query_one("#openai-key", Input).value
        anthropic_key = self.query_one("#anthropic-key", Input).value
        llm_provider = self.query_one("#llm-select", Select).value
        mode = self.query_one("#mode-select", Select).value
        identity = self.query_one("#identity-select", Select).value  # NEW: capture identity

        if glm_key:
            os.environ["GLM_API_KEY"] = glm_key
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key

        return {
            "glm_key": glm_key,
            "openai_key": openai_key,
            "anthropic_key": anthropic_key,
            "provider": llm_provider,  # FIXED: was llm_provider
            "mode": mode,
            "identity": identity,  # NEW: return identity
        }
