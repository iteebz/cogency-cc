from pathlib import Path

def root(start_path: Path = None) -> Path | None:
    """Walk up from start_path to find .cogency/ directory."""
    current = start_path or Path.cwd()

    for parent in [current] + list(current.parents):
        if (parent / ".cogency").exists():
            return parent

    return None
