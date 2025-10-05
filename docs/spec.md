# cogency-code

Date: 2025-10-02

**A TUI agent built by cogency, for cogency, with cogency.**

## Vision

Every TUI agent interface is bloated shit. Overengineered React-in-terminal nonsense with 50 dependencies and baroque configuration. We build the opposite: a clean, beautiful, fast interface that dogfoods cogency as both the library and the implementation tool.

**Core thesis:** The best way to prove an agent library works is to use it to build and maintain its own interface.

## Architecture

### Pure Streaming Flow

```
cogency.Agent → async event stream → Textual widgets → terminal
```

No state management. No reducers. No bullshit. Events flow from agent to screen.

### Event Types

Already defined in `cogency/core/protocols.py`:

```python
Event = TypedDict{
    "type": "think" | "call" | "result" | "respond" | "metrics" | "end"
    "content": str
    "payload": dict  # For structured data (tool results, metrics)
    "timestamp": float
}
```

Textual widgets consume these directly. Zero transformation layer.

### Components

```
┌─ cogency-code ─────────────────────────────────────────────┐
│ claude-sonnet-4-5 • session: dev_work • resume mode       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ > Reading src/config.py                                    │
│ ● Read src/config.py                                       │
│                                                            │
│ ~ The validation logic at line 47 assumes non-null        │
│   but the schema definition allows it. Classic type       │
│   mismatch. Let me fix this.                              │
│                                                            │
│ ○ Editing src/config.py                                    │
│ ● Updated src/config.py                                    │
│                                                            │
│ > Fixed. Added null check before validation.              │
│                                                            │
├────────────────────────────────────────────────────────────┤
│ % 2,134➜891 tokens | 3.2s                                  │
├────────────────────────────────────────────────────────────┤
│ › fix the validation bug_                            [⚙︎]  │
└────────────────────────────────────────────────────────────┘
```

**Header:** Model, session, mode
**Stream:** Event rendering with semantic formatting
**Metrics:** Token efficiency, timing
**Input:** Natural language with history
**Config:** [⚙︎] panel for API keys, tools, settings

### Widget Hierarchy

```python
App (Textual)
├─ Header
│  ├─ ModelInfo (dynamic: llm name)
│  ├─ SessionInfo (conversation_id)
│  └─ ModeIndicator (resume/replay/auto)
├─ StreamView
│  └─ EventLog (scrollable, auto-scroll on new events)
│     ├─ ThinkEvent (dimmed, italics)
│     ├─ RespondEvent (bright, main content)
│     ├─ CallEvent (○ symbol, action description)
│     └─ ResultEvent (● symbol, outcome)
├─ Footer
│  ├─ MetricsDisplay (input➜output|duration)
│  └─ InputBar (with [⚙︎] trigger)
└─ ConfigPanel (modal overlay)
   ├─ APIKeyManager
   ├─ ModelSelector
   ├─ ToolToggle
   └─ ModeSelector
```

## Implementation Strategy

### Phase 1: Skeleton
- Textual app with basic layout
- StreamView that consumes `agent()` event stream
- Input bar that triggers new agent calls
- Static header/footer

### Phase 2: Event Rendering
- Map event types to visual components
- Format tool calls using `tools/format.py` (already exists)
- Metrics display from event["payload"]
- Auto-scroll behavior

### Phase 3: Configuration
- Config panel overlay
- API key management (env vars + runtime)
- Model selection (openai/anthropic/gemini)
- Tool category filtering
- Mode selection (resume/replay/auto)

### Phase 4: Dogfooding
- Use cogency-code to improve cogency-code
- "make the metrics prettier"
- "add syntax highlighting to code in responses"
- "optimize the scroll performance"
- Agent edits its own source via file tools

## Technical Details

### Dependencies

```toml
[tool.poetry.dependencies]
python = ">=3.11,<4.0"
cogency = "^3.0.2"
textual = "^0.63.0"
```

**That's it.** No rich, no prompt-toolkit, no bullshit. Textual includes everything.

### Project Structure

```
public/cogency-code/
├─ pyproject.toml
├─ README.md
├─ src/
│  └─ cogency_code/
│     ├─ __init__.py
│     ├─ __main__.py          # Entry point
│     ├─ app.py               # Main Textual app
│     ├─ widgets/
│     │  ├─ stream.py         # StreamView event consumer
│     │  ├─ header.py         # Header info
│     │  ├─ footer.py         # Metrics + input
│     │  └─ config.py         # Config panel
│     ├─ events.py            # Event rendering logic
│     └─ state.py             # Minimal session state
└─ tests/
   └─ test_stream.py
```

### Core Loop

```python
# app.py
class CogencyCode(App):
    def __init__(self, agent: Agent):
        self.agent = agent
        self.conversation_id = None
        self.user_id = None
        
    async def on_mount(self):
        self.stream_view = self.query_one(StreamView)
        
    async def handle_query(self, query: str):
        """User submitted input - stream agent response"""
        async for event in self.agent(
            query,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            chunks=False  # Semantic mode
        ):
            await self.stream_view.add_event(event)
            
            if event["type"] == "metrics":
                self.update_metrics(event["payload"])
```

**Zero state management.** Events flow through, widgets react.

### Event Rendering

```python
# events.py
def render_event(event: Event) -> RenderableType:
    """Transform cogency event to Textual renderable"""
    match event["type"]:
        case "think":
            return Text(f"~ {event['content']}", style="dim italic")
        case "respond":
            return Text(f"> {event['content']}", style="bold")
        case "call":
            from cogency.tools import tools
            from cogency.tools.parse import parse_tool_call
            call = parse_tool_call(event["content"])
            tool = tools.get(call.name)
            action = tool.describe(call.args) if tool else f"Tool {call.name} not available"
            return Text(f"○ {action}", style="cyan")
        case "result":
            outcome = event["payload"]["outcome"]
            return Text(f"● {outcome}", style="green")
        case "metrics":
            return None  # Handled by footer
```

Uses cogency's existing format/parse tooling. Zero duplication.

### Configuration

```python
# state.py
@dataclass
class Config:
    """Runtime configuration - persisted to ~/.cogency-code/config.json"""
    llm: str = "anthropic"
    mode: str = "auto"
    user_id: str | None = None
    tools: list[str] = field(default_factory=lambda: ["file", "web", "memory"])
    
    # API keys loaded from env, can be overridden in UI
    openai_key: str | None = None
    anthropic_key: str | None = None
    gemini_key: str | None = None
```

### API Key Management

```python
# widgets/config.py
class APIKeyManager(Widget):
    """Secure API key input - masked display"""
    
    def render_key_status(self, provider: str) -> str:
        key = os.getenv(f"{provider.upper()}_API_KEY")
        if key:
            return f"✓ {provider} (env)"
        elif self.config.get(f"{provider}_key"):
            return f"✓ {provider} (runtime)"
        else:
            return f"✗ {provider}"
```

Respects env vars first, allows runtime override.

### Dogfooding Loop

```python
# When user types: "make the stream scroll smoother"

# cogency-code passes this to its own agent
async for event in agent("make the stream scroll smoother"):
    # Agent uses file_search to find widgets/stream.py
    # Agent reads StreamView implementation
    # Agent identifies scroll refresh rate
    # Agent uses file_edit to optimize
    # Agent responds with what it changed
    
# User sees the change immediately
# Can continue: "now make it even faster"
```

**Self-improving through natural language.** This is the vision.

## Design Principles

### 1. Zero Ceremony
No configuration files unless absolutely necessary. Sane defaults. Environment variables for secrets.

### 2. Pure Functions
Widgets are pure consumers of event streams. No internal state machines.

### 3. Textual Native
Use Textual's built-in styling, layout, reactivity. Don't fight the framework.

### 4. Cogency-First
If cogency has it, use it. Format tools? Use `tools/format.py`. Parse calls? Use `tools/parse.py`. Don't reinvent.

### 5. Self-Modification
The interface improves itself by running cogency against its own source code.

## Comparison to Alternatives

### Claude Code (reference implementation)
- Electron app, thousands of dependencies
- Complex IPC between main/renderer processes
- Custom prompt engineering per provider
- **cogency-code:** Terminal native, 2 dependencies, uses cogency's prompts

### Codex/Gemini CLI
- Basic REPL, no streaming visualization
- No session persistence
- No self-modification capability
- **cogency-code:** Rich streaming UI, persistent sessions, dogfoods itself

### Aider, Continue, etc.
- File-centric, not conversation-centric
- Opinionated workflows
- Limited introspection
- **cogency-code:** Conversation-first, emergent behavior, full transparency

## Success Criteria

1. **Functional:** Can execute multi-turn reasoning tasks with tool use
2. **Beautiful:** Clean visual hierarchy, readable events, smooth scrolling
3. **Dogfoodable:** Can improve its own code via natural language
4. **Fast:** Event rendering <16ms, token streaming real-time
5. **Stable:** Handles WebSocket reconnection, API errors gracefully

## Anti-Goals

- **NOT** a code editor (use your own)
- **NOT** a file browser (agent has file tools)
- **NOT** a git client (agent has shell tool)
- **NOT** configurable themes (one beautiful default)
- **NOT** plugin architecture (use cogency's Tool protocol)

## Timeline

- **Week 1:** Skeleton + basic streaming
- **Week 2:** Event rendering + config panel
- **Week 3:** Dogfooding + stability
- **Week 4:** Polish + release

## Open Questions

1. **Session discovery:** List past conversations? Or just manual ID entry?
2. **Multi-session:** Tabs? Or single-session purity?
3. **Export:** Save conversation to markdown?
4. **Syntax highlighting:** In streamed code blocks?
5. **Voice input:** For resume mode, could be interesting

## Installation

```bash
# Install from PyPI
pip install cogency-code

# Or with uvx
uvx cogency-code

# Run
cogency-code

# With specific model
cogency-code --llm anthropic

# Resume existing session
cogency-code --session dev_work --user alice
```

## First-Run Experience

```
Welcome to cogency-code

No API keys detected. Configure now? [Y/n] y

Anthropic API key: sk-ant-***_
OpenAI API key (optional): [skip]
Google API key (optional): [skip]

Keys saved to ~/.cogency-code/config.json

Ready. What would you like to build?
›_
```

**Zero friction.** First query within 30 seconds.

---

**This is the spec. Clean. Minimal. Dogfoodable. Let's build it.**
