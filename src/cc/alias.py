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


def get_model_from_alias(alias: str) -> tuple[str, str] | None:
    """
    Retrieves the provider and model name from MODEL_ALIASES based on a given alias.

    Args:
        alias: The alias to look up (case-insensitive).

    Returns:
        A tuple (provider, model) if the alias is found, otherwise None.
    """
    for key, value in MODEL_ALIASES.items():
        if key.lower() == alias.lower():
            return value["provider"], value["model"]
    return None
