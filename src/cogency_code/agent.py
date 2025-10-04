from cogency.core.agent import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from .identities import get_identity
from .instructions import load_instructions
from .llms.glm import GLM
from .state import Config


def create_agent(app_config: Config) -> Agent:
    llm = _create_llm(app_config.provider, app_config)

    instructions = load_instructions()
    identity = get_identity(app_config.identity)

    return Agent(
        llm=llm,
        max_iterations=10,
        security=Security(access="project"),
        identity=identity,
        instructions=instructions,
        mode="auto",
    )


def _create_llm(provider_name: str, app_config: Config):
    providers = {
        "glm": GLM,
        "openai": OpenAI,
        "anthropic": Anthropic,
        "gemini": Gemini,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    api_key = app_config.get_api_key(provider_name)
    return providers[provider_name](api_key=api_key)
