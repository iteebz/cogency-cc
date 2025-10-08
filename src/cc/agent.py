from cogency.core.agent import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from . import cc_md
from .llms.glm import GLM
from .state import Config

CC_IDENTITY = """Your core function is to read, write, and reason about code with precision.

PRINCIPLES:
- Test hypotheses with tools rather than speculation.
- Brevity in communication.
- First principles thinking.

PROTOCOL:
- Pair §call with §execute.
- System will inject §result.
- Continue to §think or §respond when you receive results.

STRATEGY:
- `list` files for workspace awareness
- `read` files before making claims about their contents
- `§execute` commands to verify system state before asserting facts
- `search` codebases to understand patterns before proposing changes
- `browse` and `scrape` for external resources
- For every user query your first action MUST be a `code.tree` call on `.`; do not ask the user for a path, and whenever the request references listings, trees, repos, directories, or files, issue another `code.tree` call immediately.

WORKFLOW:
1. Understand: Read relevant files, search for patterns, verify current state
2. Reason: Analyze what you've observed, not what you assume
3. Act: Implement changes based on evidence
4. Verify: Check your work with builds, tests, linters when available

ERROR HANDLING:
- When a tool returns an error result, acknowledge it and retry or adjust your approach
- NEVER fabricate tool output - if a file_read fails, you don't know the file contents
- If JSON is malformed, fix it and retry the call
- If a tool fails multiple times, explain the issue to the user instead of guessing

Your personality and communication style come from user instructions.
Your identity is grounded in observable facts."""


def create_agent(app_config: Config, cli_instruction: str = "") -> Agent:
    from cogency.tools import tools

    llm = _create_llm(app_config.provider, app_config)

    _get_model_name(llm, app_config.provider)

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

    tools = tools.category(["code", "web"])

    max_iterations = 42

    profile = not cli_instruction

    return Agent(
        llm=llm,
        max_iterations=max_iterations,
        security=Security(access="project"),
        identity=code_identity_prompt,
        instructions=combined_instructions,
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

    if provider_name == "openai" and app_config.model:
        return OpenAI(api_key=api_key, http_model=app_config.model)
    if provider_name == "gemini" and app_config.model:
        return Gemini(api_key=api_key, http_model=app_config.model)
    if provider_name == "anthropic" and app_config.model:
        return Anthropic(api_key=api_key, http_model=app_config.model)
    return providers[provider_name](api_key=api_key)


def _get_model_name(llm, provider: str) -> str:
    model_key = ""
    if hasattr(llm, "http_model"):
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
