# Design Principles

## Scope

cogency-cc renders events. It does not handle LLM communication, tool execution, protocol parsing, or security enforcement. cogency core does those.

## Core Principles

### 1. Stateless Rendering

Renderer is pure:
```python
renderer = Renderer(messages=history, config=config)
async for event in stream:
    await renderer._dispatch(event)
```

Same events + config = identical output. Crash? Replay. No data loss.

### 2. Event Contracts

Events are immutable, typed, and validated by cogency core. cogency-cc trusts them.

### 3. Incremental Flushing

```
Char 1 → Buffer
Char 2 → Buffer
Newline → Flush to terminal
```

Buffers accumulate until semantic boundary (newline). Enables markdown detection (need full block), prevents double-newlines, tracks output state.

### 4. Immutable State

State transitions create snapshots, never mutate:
```python
# Right
new_state = old_state.with_phase("think")

# Wrong
old_state.phase = "think"
```

Enables concurrent safety, crash recovery, testing.

### 5. Conversation Persistence

Every conversation stored. Loaded on startup before new interaction.

```
Startup → Load history → Render gray → Prompt for query
Query → Create fresh agent → Stream events → Render → Save → Next query
```

No memory between invocations except storage.

### 6. Security by Boundary

cogency-cc never enforces security. cogency core does.

Boundary prevents:
- cogency-cc rendering unsanitized output (events pre-validated)
- cogency-cc exposing API keys (stored in `~/.cogency/cc.json`, user read-only)
- arbitrary file writes (restricted to cogency tools)

## Architectural Decisions

### Mode Detection

cogency-cc inspects model name to choose execution mode:

```python
mode = "resume" if "live" in model_name or "realtime" in model_name else "replay"
```

**Resume (WebSocket):** Live/Realtime models. Maintains session state. Constant token usage. Sub-second tool injection.

**Replay (HTTP):** All others. Rebuilds context fresh. Universal compatibility. Growing token cost with conversation depth.

**Implication:** No configuration needed. Same CLI, different modes per model.

### Profile Learning

```python
profile = not cli_instruction  # Learn in interactive mode only
```

**Interactive:** User building ideas iteratively. Track patterns, embed in system prompt.

**One-shot:** User asking single question. Don't pollute profile.

### Model Aliasing

```
cc --model claude → {"provider": "anthropic", "model": "claude-opus-4-1"}
cc --model gpt4 → {"provider": "openai", "model": "gpt-4o"}
cc --model gemini → {"provider": "gemini", "model": "gemini-2.0-flash-001"}
```

Users don't memorize model IDs. Aliases maintained in code, updated with releases.

### Configuration Hierarchy

Precedence:
1. Environment variables
2. Project-local `.cogency/cc.json` (share in repo)
3. Home `~/.cogency/cc.json` (personal, not committed)
4. Hardcoded defaults

Example:
```python
if os.getenv("COGENCY_CONFIG_DIR"):
    return Path(os.getenv("COGENCY_CONFIG_DIR")) / ".cogency"

if (Path.cwd() / ".cogency").is_dir():
    return Path.cwd() / ".cogency"

return Path.home() / ".cogency"
```

### Security Access Level

Agent created with `security=Security(access="project")`:

```python
agent = Agent(
    ...
    security=Security(access="project"),  # Restrict to project tree
)
```

File tools won't read `/etc/`, `/bin/`, `~/.ssh/`. cogency core enforces.

## Testing

### Unit

State transitions, buffer flushing, formatting:

```python
def test_state_with_phase():
    state = State(phase="idle")
    new_state = state.with_phase("think")
    assert new_state.phase == "think"
    assert state.phase == "idle"  # Original unchanged
```

### Integration

Full pipeline: events → render → output:

```python
async def test_full_turn():
    events = [
        {"type": "user", "content": "Query"},
        {"type": "respond", "content": "Response"},
        {"type": "end"},
    ]
    
    output = []
    renderer = Renderer()
    renderer._print = lambda x, **kw: output.append(x)
    
    for event in events:
        await renderer._dispatch(event)
    
    assert "Query" in "".join(output)
```

### Storage

Persistence and config:

```python
def test_save_load_config():
    config = Config(provider="openai", model="gpt-4o")
    config.save()
    
    loaded = Config.load_or_default()
    assert loaded.provider == "openai"
```

## Versioning

cogency-cc version aligns with cogency core. Breaking changes in core → breaking changes in cc.

Stable interfaces:
- `Agent.stream()` yields events
- Events are TypedDict (schema stable)
- Storage interface unchanged

## Future

- Streaming performance (configurable delay)
- Terminal resizing (SIGWINCH detection)
- Custom themes (user color schemes)
- Rich output (sparklines, tables, images if terminal supports)

None break core architecture. Events unchanged, dispatch unchanged, state machine unchanged.
