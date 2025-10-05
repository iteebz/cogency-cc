"""Tests for identity functions."""

import pytest

from cc.identity import CODING_IDENTITY, get_identity, list_identity


def test_list_identity():
    """Test listing available identities."""
    identity = list_identity()
    expected = ["coding", "cothinker", "assistant"]
    assert identity == expected

def test_get_identity_coding():
    """Test getting coding identity."""
    identity = get_identity("coding")
    assert "Cogency Code" in identity
    assert "coding agent" in identity
    assert "read, write, and reason about code" in identity

def test_get_identity_cothinker():
    """Test getting cothinker identity."""
    identity = get_identity("cothinker")
    assert "Cothinker" in identity
    assert "critical thinking partner" in identity
    assert "prevent bad implementations" in identity

def test_get_identity_assistant():
    """Test getting assistant identity."""
    identity = get_identity("assistant")
    assert "helpful assistant" in identity
    assert "accommodating and supportive" in identity

def test_get_identity_unknown():
    """Test error for unknown identity."""
    with pytest.raises(ValueError, match="Unknown identity 'unknown'"):
        get_identity("unknown")

def test_coding_identity_structure():
    """Test that CODING_IDENTITY contains required elements."""
    assert "Cogency Code" in CODING_IDENTITY
    assert "OPERATIONAL PRINCIPLES" in CODING_IDENTITY
    assert "WORKFLOW" in CODING_IDENTITY
    assert "ERROR HANDLING" in CODING_IDENTITY

    # Verify key principles are present
    assert "Read files before making claims" in CODING_IDENTITY
    assert "Accuracy > speed" in CODING_IDENTITY
    assert "NEVER fabricate tool output" in CODING_IDENTITY