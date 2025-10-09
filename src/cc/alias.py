"""CLI aliases for models."""

MODEL_ALIASES = {
    "codex": {"provider": "openai", "model": "gpt-5-codex"},
    "gemini": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "gemini-live": {"provider": "gemini", "model": "gemini-1.5-flash-latest"},
    "sonnet": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    "gpt4o": {"provider": "openai", "model": "gpt-4o"},
    "4o": {"provider": "openai", "model": "gpt-4o-mini"},
    "4o-live": {"provider": "openai", "model": "gpt-4o-mini-realtime-preview"},
}
