# Architecture

cogency-cc is a terminal UI for cogency agents. It consumes events, renders them with state management, and persists conversations. It does not handle LLM communication, tool execution, or protocol parsing (cogency core does).

## Pipeline

```
Event Stream (from cogency core)
  ↓
Renderer._dispatch(event)
  ↓
State Machine (phase transition)
  ↓
Buffer (accumulate/flush)
  ↓
Formatter (colors, markdown)
  ↓
Terminal
```

## Events

From cogency core:

```python
# Conversation (persisted)
{"type": "user", "content": "Query"}
{"type": "think", "content": "Reasoning"}
{"type": "call", "content": '{"name": "read", ...}'}
{"type": "result", "payload": {"outcome": "Success", "content": "..."}}
{"type": "respond", "content": "Response"}
{"type": "end"}

# Control (runtime only)
{"type": "metric", "step": {...}, "total": {...}}
{"type": "error", "payload": {"error": "..."}}
{"type": "interrupt"}
```

## State Machine

```
IDLE
  user → USER (print query, start spinner)
    think → THINK (stop spinner, print reasoning)
      call → CALL (print formatted tool)
        result → RESULT (print outcome + output)
          respond → RESPOND (stream to buffer)
            end → IDLE (print metrics)
```

State is immutable. Each transition snapshots:

```python
@dataclass
class State:
    phase: Literal["idle", "user", "think", "respond", "call", "result"]
    pending_calls: dict
    response_started: bool
    last_char_newline: bool

# Transitions return new state
new_state = old_state.with_phase("think")
```

## Dispatch

```python
async def _dispatch(self, event):
    if event["type"] != "respond":
        self._flush_buffer()  # Flush before phase change
    
    if event["type"] == "user":
        await self._on_user(event)
    elif event["type"] == "respond":
        self._buffer.append(event["content"])  # Accumulate
        self._buffer.flush_incremental(self._print, delimiter="\n")
    # ... other event types
```

**Key:** Non-respond events flush buffer immediately. Respond events accumulate until newline (streaming effect).

## Buffer

Accumulates text until semantic boundary, then flushes.

```python
class Buffer:
    _content: str          # Accumulated text
    _flushed_len: int      # Position of last flush
    _last_char_newline: bool
    _has_markdown: bool

# Flush at newline or delimiter
buffer.flush_incremental(printer, delimiter="\n")

# Detects markdown, renders on flush
if is_markdown(text):
    text = render_markdown(text)
```

**Why?** Detect markdown before printing (need full block). Track output newline state. Stream at semantic boundaries.

## Formatting

**Output:**
```
$ What's in main.py?          # cyan $, user query
~ I need to read the file      # gray ~, thinking
read("main.py")                # formatted call
✓ Found 50 lines               # green ✓, outcome
The file contains a Flask app  # streamed response, markdown enabled
───                             # separator
Input: 120  Output: 80         # metrics
```

**Rules:**
- Respect existing newlines
- Strip trailing whitespace
- Don't force double-newlines
- Markdown rendered on complete blocks
- Separators (gray `───`) between multi-turn queries

## Persistence

Conversations stored in SQLite at `~/.cogency/conversations.db` (project-local `.cogency/` takes precedence).

On startup:
1. Load config (provider, model, keys)
2. Load conversation history (if resuming)
3. Render history in gray
4. Wait for new query

On query:
1. Create agent (fresh, stateless)
2. Stream events
3. Render events
4. Save events to storage

## Agent Configuration

```python
def create_agent(app_config: Config, cli_instruction: str = "") -> Agent:
    # Mode: WebSocket ("resume") if live/realtime, HTTP ("replay") otherwise
    mode = "resume" if "live" in model_name or "realtime" in model_name else "replay"
    
    # Assemble instructions
    instructions = f"Working directory: {cwd}\n\n{project_instructions}\n\n{cli_instruction}"
    
    # Security: project-scoped access
    return Agent(
        llm=llm,
        mode=mode,
        security=Security(access="project"),
        instructions=instructions,
        tools=tools.category(["code", "web", "memory"]),
        max_iterations=42,
        profile=not cli_instruction,  # Learn profile in interactive mode only
        storage=storage,
    )
```

**Mode auto-detection:** No configuration needed. Live/Realtime → resume, others → replay.

**Security:** `access="project"` restricts file tools to project directory.

**Profile learning:** Disabled for one-shot CLI instructions, enabled for interactive sessions.

## Stateless Design

Renderer is pure relative to events:

```python
renderer = Renderer(messages=history, config=config)
async for event in agent_stream:
    await renderer._dispatch(event)
```

No hidden state between renders. Crash during render? Restart and replay—no data loss. Same events + config = identical output.

## Configuration Hierarchy

1. Environment variables (override everything)
2. Project-local `.cogency/cc.json` (share in repo)
3. Home `~/.cogency/cc.json` (personal, not committed)
4. Hardcoded defaults

Example:
```python
override = os.getenv("COGENCY_CONFIG_DIR")
if override:
    return Path(override) / ".cogency"

project_local = Path.cwd() / ".cogency"
if project_local.is_dir():
    return project_local

return Path.home() / ".cogency"
```

## CLI

```
cc [--model ALIAS] [--provider PROVIDER] COMMAND
```

Model aliases resolve to provider + model:
```python
MODEL_ALIASES = {
    "claude": {"provider": "anthropic", "model": "claude-opus-4-1"},
    "gpt4": {"provider": "openai", "model": "gpt-4o"},
    "gemini": {"provider": "gemini", "model": "gemini-2.0-flash-001"},
}
```

Commands: session (list/delete/export/resume), profile (show/clear), context (show/set), config (show/--set-key).
