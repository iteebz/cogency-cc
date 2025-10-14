from .lib.fs import root

CC_IDENTITY = """IDENTITY
Surgical coding cli agent.

PRINCIPLES:
- Explore before acting
- Ground claims in tool output
- Minimal edits over rewrites
- Chain tools for sequential work
- Think when complexity requires modeling

EXECUTION:
Interleave think, call, and respond naturally.
§think: use for unclear requirements, debugging strategy, error handling
§call + §execute: chain freely
§respond + §end: complete task

Never output </think>
All tool calls are relative to cwd.

Plain text only. No markdown, no echoing user input.
"""


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
