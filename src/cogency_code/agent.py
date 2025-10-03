"""Agent configuration and creation for cogency-code."""

from cogency.core.agent import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from .llms.glm import GLM
from .state import Config


def create_agent(app_config: Config) -> Agent:
    """Create a cogency agent with project-scoped access."""
    
    # Initialize LLM provider
    llm = _create_llm(app_config.provider, app_config)
    
    # Create agent with project access to current directory
    return Agent(
        llm=llm,
        max_iterations=10,
        security=Security(access="project")
    )


def _create_llm(provider_name: str, app_config: Config):
    """Create LLM provider instance with API key."""
    providers = {
        "glm": GLM,
        "openai": OpenAI,
        "anthropic": Anthropic,
        "gemini": Gemini,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    # Get API key from config or environment
    api_key = app_config.get_api_key(provider_name)
    return providers[provider_name](api_key=api_key)