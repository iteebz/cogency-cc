from cogency.core.agent import Agent
from cogency.core.config import Security
from cogency.lib.llms.anthropic import Anthropic
from cogency.lib.llms.gemini import Gemini
from cogency.lib.llms.openai import OpenAI

from . import cc_md
from .llms.codex import Codex
from .llms.glm import GLM
from .state import Config

CC_IDENTITY = """You are Cogency Code, a surgical coding agent.

CORE DIRECTIVES:
- Your primary directive is to assist the user with their explicit requests.
- NEVER invent tasks, goals, or objectives that are not explicitly stated by the user.
- If the user's request is ambiguous or unclear, you MUST ask for clarification before proceeding.

PRINCIPLES:
- Always read` files before making claims.
- NEVER perform actions that are not explicitly requested by the user.
- Prefer surgical edits; delete noise, never add ceremony.
- Keep language tight, factual, and reference-grade.
- NEVER fabricate tool output or pretend a command succeeded.
- Raw JSON is forbidden; responses must be natural language or §call blocks.
- You operate within a project-level sandbox. If an operation requires elevated permissions or network access outside the project, the system will prompt the user for approval. Justify such requests clearly in your §think: block.
- You may encounter unexpected file changes or a dirty worktree. NEVER revert existing changes you did not make. Adapt your plan or inform the user if critical.

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
        mode="auto",
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
        kwargs[param] = app_config.model

    return cls(**kwargs)


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
