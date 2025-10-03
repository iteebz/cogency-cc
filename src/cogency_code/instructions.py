"""Load project instructions from COGENCY.md."""

from pathlib import Path


def find_project_root(start_path: Path = None) -> Path | None:
    """Walk up from start_path to find .cogency/ directory."""
    current = start_path or Path.cwd()
    
    for parent in [current] + list(current.parents):
        if (parent / ".cogency").exists():
            return parent
    
    return None


def load_instructions() -> str | None:
    """Load COGENCY.md from project root if it exists."""
    root = find_project_root()
    
    if not root:
        return None
    
    cogency_md = root / "COGENCY.md"
    
    if cogency_md.exists():
        return cogency_md.read_text(encoding="utf-8")
    
    return None
