from cogency import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from . import cc_md
from .config import Config
from .llms.glm import GLM
from .llms.mlx import MLX
from .storage import storage as get_storage

__all__ = ["create_agent"]


def create_agent(app_config: Config, cli_instruction: str = "") -> Agent:
    from pathlib import Path

    from cogency.tools import code, memory, web

    model_name = app_config.model or ""
    mode = "resume" if "live" in model_name or "realtime" in model_name else "replay"

    project_instructions = cc_md.load() or ""

    cwd = Path.cwd()
    instructions = f"Working directory: {cwd}"
    if project_instructions:
        instructions += f"\n\n{project_instructions}"
    if cli_instruction:
        instructions += f"\n\n{cli_instruction}"

    tools = code + web + memory
    llm = _create_llm(app_config.provider, app_config)
    storage = get_storage(app_config)

    identity = """Execute tasks. Minimal tool calls. Terse output.
No exploration. No explanation. Just results."""

    return Agent(
        llm=llm,
        max_iterations=42,
        security=Security(access="project"),
        identity=identity,
        instructions=instructions,
        tools=tools,
        mode=mode,
        profile=not cli_instruction,
        storage=storage,
    )


def _create_llm(provider_name: str, app_config: Config):
    providers = {
        "glm": GLM,
        "mlx": MLX,
        "openai": OpenAI,
        "anthropic": Anthropic,
        "gemini": Gemini,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    api_key = app_config.get_api_key(provider_name)
    llm_class = providers[provider_name]

    model_name = app_config.model
    if not model_name:
        return llm_class(api_key=api_key)

    is_websocket = "live" in model_name or "realtime" in model_name

    if is_websocket:
        return llm_class(api_key=api_key, websocket_model=model_name)
    return llm_class(api_key=api_key, http_model=model_name)
