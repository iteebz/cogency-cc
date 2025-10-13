"""Tests for cc.md loading logic."""

from pathlib import Path
from unittest.mock import patch

import pytest

from cc.cc_md import load


@pytest.fixture
def mock_root(tmp_path: Path) -> Path:
    """Provides a mock project root directory."""
    (tmp_path / ".cogency").mkdir()
    return tmp_path

    def test_load_cc_md_exists(mock_root: Path):
        """Should load content when .cogency/cc.md exists."""
        cc_md_file = mock_root / ".cogency" / "cc.md"
        cc_md_file.write_text("Custom instructions")

        with patch("cc.lib.fs.root", return_value=mock_root):
            content = load()
            assert content == "--- User cc.md ---\nCustom instructions\n--- End cc.md ---"

    return None


def test_load_cc_md_is_empty(mock_root: Path):
    """Should return an empty string if cc.md is empty."""
    cc_md_file = mock_root / ".cogency" / "cc.md"
    cc_md_file.write_text("")

    with patch("cc.lib.fs.root", return_value=mock_root):
        content = load()
        assert content == ""


def test_load_cc_md_is_whitespace(mock_root: Path):
    """Should return an empty string if cc.md contains only whitespace."""
    cc_md_file = mock_root / ".cogency" / "cc.md"
    cc_md_file.write_text("   \n  ")

    with patch("cc.lib.fs.root", return_value=mock_root):
        content = load()
        assert content == ""


def test_load_cc_md_does_not_exist(mock_root: Path):
    """Should return an empty string if cc.md does not exist."""
    with patch("cc.lib.fs.root", return_value=mock_root):
        content = load()
        assert content == ""
