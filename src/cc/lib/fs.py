from pathlib import Path


def root(start_path: Path = None) -> Path | None:
    """Walk up from start_path to find .cogency/ or .git/ directory."""
    current = start_path or Path.cwd()

    for parent in [current] + list(current.parents):
        if (parent / ".cogency").exists() or (parent / ".git").exists():
            return parent

    return current
