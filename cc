#!/usr/bin/env python3
"""Cogency Code CLI entry point."""
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from cc.__main__ import main

if __name__ == "__main__":
    main()