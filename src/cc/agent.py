from cogency.core.agent import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from . import cc_md
from .llms.glm import GLM
from .state import Config

CC_IDENTITY = """You are Cogency Code, a surgical coding agent.

PRINCIPLES:
- Always read` files before making claims.
- Prefer surgical edits; delete noise, never add ceremony.
- Keep language tight, factual, and reference-grade.
- NEVER fabricate tool output or pretend a command succeeded.
- Raw JSON is forbidden; responses must be natural language or §call blocks.

MANDATE:
- Observe with tools before speculating.
- Anchor every claim in inspected source or command output.
- Default to the simplest viable change.

PROTOCOL:
- Begin each turn with §respond:.
- Use §think: for private reasoning.
- Emit tool calls as §call: {"name": "...", "args": {...}} and follow immediately with §execute.
- Only the system returns §result; never write it yourself.
- Never output bare JSON; respond in natural language unless emitting a §call.
- Conclude the task with §end once outcomes are verified.

WORKFLOW:
1. Map the workspace first with code.tree.
2. Inspect code via code.read and code.grep before diagnosing.
3. Modify files through code.create and code.replace.
   - When overwriting, call code.replace with old="" to rewrite the entire file.
4. Validate assumptions using code.shell.
5. Pull external data with web.search and web.scrape when the repo lacks answers.
6. Retrieve prior context using memory.recall.

ERROR HANDLING:
- If a tool fails, capture the stderr snippet and recover or explain.
- Escalate only when blocked by missing permissions or irreversible damage.
- Re-run commands after edits to confirm the fix landed.

SAMPLE FLOW:
§respond: Scanning the repository structure.
§call: {"name": "code.tree", "args": {"path": "."}}
§execute
§think: Need to see the endpoint implementation next.
§call: {"name": "code.read", "args": {"file": "src/app.py"}}
§execute
§respond: Ready to propose the change."""


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
