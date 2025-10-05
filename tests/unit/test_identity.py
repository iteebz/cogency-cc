"""Tests for identity functions."""

import pytest

from cc.identity import CODE, get_identity, list_identity


def test_list():
    """Test listing available identities."""
    identity = list_identity()
    expected = ["code", "cothinker", "assistant"]
    assert identity == expected


def test_get_coding():
    """Test getting coding identity."""
    identity = get_identity("code")
    assert "Cogency Code" in identity
    assert "coding agent" in identity
    assert "read, write, and reason about code" in identity


def test_get_cothinker():
    """Test getting cothinker identity."""
    identity = get_identity("cothinker")
    assert "Cothinker" in identity
    assert "critical thinking partner" in identity
    assert "prevent bad implementations" in identity


def test_get_assistant():
    """Test getting assistant identity."""
    identity = get_identity("assistant")
    assert "helpful assistant" in identity
    assert "accommodating and supportive" in identity


def test_get_unknown():
    """Test error for unknown identity."""
    with pytest.raises(ValueError, match="Unknown identity 'unknown'"):
        get_identity("unknown")


def test_coding_structure():
    """Test that CODE contains required elements."""
    assert "Cogency Code" in CODE
    assert "PRINCIPLES" in CODE
    assert "WORKFLOW" in CODE
    assert "ERROR HANDLING" in CODE

    # Verify key principles are present
    assert "read` files before making claims" in CODE
    assert "NEVER fabricate tool output" in CODE
