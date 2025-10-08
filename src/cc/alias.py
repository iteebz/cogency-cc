"""CLI aliases for models."""

MODEL_ALIASES = {
    "codex": {"provider": "openai", "model": "gpt-5-codex"},
    "gemini": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "gemini-live": {
        "provider": "gemini",
        "model": "gemini-1.5-flash-latest",
    },  # Assuming a common "live" model
    "sonnet": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    # Add more as needed
}
