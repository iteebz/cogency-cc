"""cc - Reference grade CLI agent."""

# Load environment variables FIRST - before any imports that need API keys
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

__version__ = "0.1.0"

from .config import Config

__all__ = ["Config"]
