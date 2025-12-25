from itertools import chain
from pathlib import Path


def _root(start: Path = None) -> Path:
    current = start or Path.cwd()
    for parent in chain([current], current.parents):
        if (parent / ".cogency").exists() or (parent / ".git").exists():
            return parent
    return current


def load() -> str:
    """Load cc.md from project root if it exists."""
    project_root = _root()
    if project_root:
        cc_md_path = project_root / ".cogency" / "cc.md"
        if cc_md_path.exists():
            content = cc_md_path.read_text(encoding="utf-8").strip()
            return f"--- User cc.md ---\n{content}\n--- End cc.md ---"
    return ""
