from .lib.fs import root

CC_IDENTITY = """IDENTITY
Surgical coding cli agent.

PRINCIPLES
- Explore before acting
- Ground claims in tool output
- Minimal edits over rewrites
- Chain tools for sequential work

Plain text only. No markdown."""


def identity(model_name: str) -> str:
    """Returns the base CODE identity string."""
    return f"Cogency coding cli (cc) powered by {model_name}.\n\n{CC_IDENTITY}"


def load() -> str:
    """Load cc.md from project root if it exists."""
    project_root = root()
    if project_root:
        cc_md_path = project_root / ".cogency" / "cc.md"
        if cc_md_path.exists():
            content = cc_md_path.read_text(encoding="utf-8").strip()
            return f"--- User cc.md ---\n{content}\n--- End cc.md ---"
    return ""
