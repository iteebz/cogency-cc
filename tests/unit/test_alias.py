"""Tests for model alias resolution."""

from cc.alias import get_model_from_alias


def test_get_model_from_alias_valid():
    """Should return the correct model for all valid aliases."""
    assert get_model_from_alias("codex") == ("openai", "gpt-5-codex")
    assert get_model_from_alias("sonnet") == ("anthropic", "claude-sonnet-4-5")
    assert get_model_from_alias("gemini") == ("gemini", "gemini-2.5-pro")
    assert get_model_from_alias("gemini-live") == ("gemini", "gemini-1.5-flash-latest")


def test_get_model_from_alias_invalid():
    """Should return None for an invalid alias."""
    assert get_model_from_alias("non-existent-alias") is None


def test_get_model_from_alias_case_insensitivity():
    """Should handle aliases in a case-insensitive manner."""
    assert get_model_from_alias("CODEX") == ("openai", "gpt-5-codex")
    assert get_model_from_alias("SoNnEt") == ("anthropic", "claude-sonnet-4-5")
