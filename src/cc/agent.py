from cogency.core.agent import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from .identity import get_identity
from .instructions import load_instructions
from .llms.glm import GLM
from .state import Config


def create_agent(app_config: Config, cli_instruction: str = "") -> Agent:
    from cogency.tools import tools

    llm = _create_llm(app_config.provider, app_config)

    instructions = cli_instruction or load_instructions()
    identity = get_identity(app_config.identity)

    model_name = _get_model_name(llm, app_config.provider)
    identity_with_model = f"You are Cogency Code powered by {model_name}.\n\n{identity}"

    tools = tools.category(["file", "system", "web"])
    max_iterations = 42
    profile = not cli_instruction

    return Agent(
        llm=llm,
        max_iterations=max_iterations,
        security=Security(access="project"),
        identity=identity_with_model,
        instructions=instructions,
        tools=tools,
        mode="auto",
        profile=profile,
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


def _get_model_name(llm, provider: str) -> str:
    if hasattr(llm, "http_model"):
        return llm.http_model
    return provider.upper()
