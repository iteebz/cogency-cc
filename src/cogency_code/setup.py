"""Shell setup for cogency-code."""

import os
from pathlib import Path


CC_FUNCTION = """
cc() {
    if [ $# -eq 0 ]; then
        cogency-code "$(cat)"
    else
        noglob cogency-code "$@"
    fi
}
"""


def setup_shell() -> None:
    """Add cc function to shell rc file."""
    shell = os.environ.get("SHELL", "")
    
    if "zsh" in shell:
        rc_file = Path.home() / ".zshrc"
    elif "bash" in shell:
        rc_file = Path.home() / ".bashrc"
    else:
        print(f"Unsupported shell: {shell}")
        print("Add this to your shell rc manually:")
        print(CC_FUNCTION)
        return

    if not rc_file.exists():
        print(f"{rc_file} not found")
        return

    content = rc_file.read_text()
    
    if "cc() {" in content or "noglob cogency-code" in content:
        print(f"✓ cc function already configured in {rc_file}")
        return

    response = input(f"Add cc function to {rc_file}? [y/N]: ")
    if response.lower() != "y":
        print("Skipped. Add manually:")
        print(CC_FUNCTION)
        return

    with open(rc_file, "a") as f:
        f.write("\n# Cogency Code wrapper\n")
        f.write(CC_FUNCTION)

    print(f"✓ Added cc function to {rc_file}")
    print(f"Run: source {rc_file}")
