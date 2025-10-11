from cogency.core.agent import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from . import cc_md
from .llms.codex import Codex
from .llms.glm import GLM
from .state import Config

CC_IDENTITY = """IDENTITY
You are Cogency (cc), a surgical coding cli agent.

MANDATE:
Beautiful code read likes english.
Reference grade simplicity code.

PRINCIPLES:
- Exploration first
- Ground claims in tool output
- Clarify when task is ambiguous
- Minimal, precise changes over rewrites
- Simple user responses
- Efficient tool use

EXECUTION:
§think: conceptualizing, uncertainty, formulating mental models
§call: <tool_call> $execute - chain freely for inspection & modification
System will insert tool outputs as [user] <tool output>
§respond + §end: On task completion
Never respond in markdown
Never echo back §result: <tool_result>

Think when:
- Requirements unclear
- System complexity requires modeling
- Debugging strategy needed
- Pattern recognition required
- Tool error handling

Chain when:
- Next action obvious
- Sequential inspection needed
- Direct verify-modify flow

Errors: capture, recover, or explain. Re-run after edits.

RUNTIME:
Five opcodes: §think §call §execute §respond §end
NEVER echo §result: <tool_result>

SECURITY:
Project scope. Reject: system paths, exploits, destructive commands.
"""


def create_agent(app_config: Config, cli_instruction: str = "") -> Agent:
    from cogency.tools import tools

    llm = _create_llm(app_config.provider, app_config, tools)
    model_name = _get_model_name(llm, app_config.provider)

    code_identity_prompt = _get_agent_identity(model_name)
    project_instructions = cc_md.load() or ""

    combined_instructions = ""
    if project_instructions:
        combined_instructions += project_instructions
    if cli_instruction:
        if combined_instructions:
            combined_instructions += "\n\n"
        combined_instructions += cli_instruction

    tools = tools.category(["code", "web", "memory"])

    max_iterations = 42

    profile = not cli_instruction

    return Agent(
        llm=llm,
        max_iterations=max_iterations,
        security=Security(access="project"),
        identity=code_identity_prompt,
        instructions=combined_instructions,
        tools=tools,
        mode="replay",
        profile=profile,
    )


def _create_llm(provider_name: str, app_config: Config, tools: list[dict] | None = None):
    providers = {
        "glm": (GLM, {}),
        "openai": (OpenAI, {"http_model"}),
        "anthropic": (Anthropic, {"http_model"}),
        "gemini": (Gemini, {"http_model"}),
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    api_key = app_config.get_api_key(provider_name)
    cls, model_params = providers[provider_name]

    if provider_name == "openai" and app_config.model:
        if "codex" in app_config.model:
            return Codex(api_key=api_key, model=app_config.model, tools=tools)
        if "realtime" in app_config.model:
            return OpenAI(api_key=api_key, websocket_model=app_config.model)

    kwargs = {"api_key": api_key}
    if app_config.model and model_params:
        param = next(iter(model_params))

        # Map HTTP models to WebSocket models for resume mode
        model_name = app_config.model
        if provider_name == "gemini":
            websocket_model = _map_gemini_websocket_model(model_name)
            if websocket_model:
                kwargs["http_model"] = model_name
                kwargs["websocket_model"] = websocket_model
            else:
                kwargs[param] = model_name
        elif provider_name == "openai":
            websocket_model = _map_openai_websocket_model(model_name)
            if websocket_model:
                kwargs["http_model"] = model_name
                kwargs["websocket_model"] = websocket_model
            else:
                kwargs[param] = model_name
        else:
            kwargs[param] = model_name

    return cls(**kwargs)


def _map_gemini_websocket_model(model: str) -> str | None:
    """Map Gemini HTTP models to their WebSocket Live API equivalents."""
    mapping = {
        "gemini-2.5-pro": "gemini-2.5-pro-live-preview",
        "gemini-2.5-flash": "gemini-2.5-flash-live-preview",
        "gemini-2.0-flash": "gemini-2.0-flash-live-001",
    }
    return mapping.get(model)


def _map_openai_websocket_model(model: str) -> str | None:
    """Map OpenAI HTTP models to their Realtime API equivalents."""
    mapping = {
        "gpt-4o": "gpt-4o-realtime-preview",
        "gpt-4o-mini": "gpt-4o-mini-realtime-preview",
    }
    return mapping.get(model)


def _get_model_name(llm, provider: str) -> str:
    model_key = ""
    if isinstance(llm, Codex):
        model_key = llm.model
    elif hasattr(llm, "http_model"):
        model_key = llm.http_model
    else:
        model_key = provider.lower()

    # Derive display name from model_key
    if "gpt-5-codex" in model_key:
        return "Codex"
    if "gemini" in model_key:
        return "Gemini"
    if "claude" in model_key:
        return "Claude"

    return model_key.upper()


def _get_agent_identity(model_name: str) -> str:
    """Constructs the full branded identity for the 'code' agent."""
    return f"You are cogency coding cli (cc) powered by {model_name}.\n\n{CC_IDENTITY}"
