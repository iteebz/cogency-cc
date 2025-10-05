"""Tests for instruction loading."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from cc.instructions import find_project_root, load_instructions


def test_load_cogency_md_priority():
    """Test that COGENCY.md takes priority over CRUSH.md."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)

        # Create both files
        (project_root / "COGENCY.md").write_text("cogency instructions")
        (project_root / "CRUSH.md").write_text("crush instructions")

        # Create .cogency directory to mark project root
        (project_root / ".cogency").mkdir()

        with patch("cc.instructions.Path.cwd", return_value=project_root):
            instructions = load_instructions()

        assert instructions == "cogency instructions"

def test_load_crush_md_fallback():
    """Test fallback to CRUSH.md when COGENCY.md doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)

        # Only create CRUSH.md
        (project_root / "CRUSH.md").write_text("crush fallback instructions")
        (project_root / ".cogency").mkdir()

        with patch("cc.instructions.Path.cwd", return_value=project_root):
            instructions = load_instructions()

        assert instructions == "crush fallback instructions"

def test_load_no_instructions():
    """Test graceful handling when no instruction files exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        (project_root / ".cogency").mkdir()

        with patch("cc.instructions.Path.cwd", return_value=project_root):
            instructions = load_instructions()

        assert instructions is None

def test_find_project_root_with_cogency_dir():
    """Test finding project root by .cogency directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        subdir = root / "subdir"
        subdir.mkdir()

        # Create .cogency in root
        (root / ".cogency").mkdir()

        # Search from subdir should find root
        found = find_project_root(start_path=subdir)
        assert found == root

def test_find_project_root_not_found():
    """Test graceful handling when no project root found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)

        with patch("cc.instructions.Path.cwd", return_value=project_root):
            found = find_project_root()
            assert found is None
