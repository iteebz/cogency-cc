"""Tests for filesystem utilities."""

from pathlib import Path
from unittest.mock import patch

from cc.lib.fs import root


def test_find_root_from_subdir(tmp_path: Path):
    """Should find the root from a subdirectory."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True)

    with patch("pathlib.Path.cwd", return_value=subdir):
        assert root() == tmp_path


def test_find_root_prefers_git(tmp_path: Path):
    """Should prefer .git over .cogency as the root marker."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".cogency").mkdir()

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        assert root() == tmp_path


def test_find_root_uses_cogency_as_fallback(tmp_path: Path):
    """Should use .cogency as a fallback if .git is not present."""
    (tmp_path / ".cogency").mkdir()

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        assert root() == tmp_path


def test_find_root_no_marker(tmp_path: Path):
    """Should return the current directory if no root marker is found."""
    with patch("pathlib.Path.cwd", return_value=tmp_path):
        assert root() == tmp_path


def test_find_root_in_parent_dir(tmp_path: Path):
    """Should find the root marker in a parent directory."""
    (tmp_path / ".git").mkdir()
    current_dir = tmp_path / "src" / "app"
    current_dir.mkdir(parents=True)

    with patch("pathlib.Path.cwd", return_value=current_dir):
        assert root() == tmp_path
