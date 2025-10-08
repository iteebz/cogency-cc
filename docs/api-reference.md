# 🧠 Cogency Agent API Reference

**Reference grade agent architecture that reads like English.**

## Quick Start

```python
from cogency_code import CogencyCode

# Launch TUI agent
app = CogencyCode()
app.run()

# Or programmatic use
async def query_agent():
    app = CogencyCode(llm_provider="glm")
    await app.handle_query("What files in current directory?")
```

## Core Agent Class

### Constructor Configuration
```python
agent = Agent(
    # CORE CAPABILITIES
    llm="openai" | LLM,           # LLM instance or string ("openai", "gemini", "anthropic")
    storage=Storage | None,       # Storage implementation (defaults to SQLite)
    base_dir=str | None,          # Base directory for file operations/storage
    
    # AGENT IDENTITY
    identity=str | None,          # Core agent identity (overrides default)
    instructions=str | None,      # Additional steering instructions
    tools=list[Tool] | None,      # Tool instances (defaults to standard set)
    
    # EXECUTION MODE
    mode="auto" | "resume" | "replay",  # Coordination mode (default: "auto")
    max_iterations=10,            # Max execution iterations
    history_window=100,           # Historical messages in context
    
    # LEARNING SYSTEM
    profile=True,                 # Enable profile learning
    learn_every=5,                # Learning frequency (every N messages)
    
    # TOOL LIMITS
    scrape_limit=3000,            # Web content character limit
    
    # SECURITY
    security=Security | None,     # Security policies
    
    # DEBUGGING
    debug=False                   # Enable verbose logging
)
```

### Main Interface Method
```python
async def __call__(
    query: str,
    user_id: str | None = None,        # User identifier (None = no profile)
    conversation_id: str | None = None, # Conversation ID (None = stateless)
    chunks: bool = False,              # True=token stream, False=semantic events
) -> AsyncGenerator[Event, None]:
    """Yields events for query processing"""
```

## Event System

### Event Types
```python
EventType = Literal[
    "think",     # LLM reasoning
    "call",      # Tool call initiation  
    "result",    # Tool result
    "respond",   # Final response
    "chunk",     # Token chunk
    "metric",    # Metrics/data
    "execute",   # Control signal (internal)
    "end",       # Control signal (internal)
]
```

### Event Structure
```python
class Event(TypedDict):
    type: EventType                    # Event type
    content: str | None               # Human-readable content
    payload: dict[str, Any] | None   # Structured data
    audience: "broadcast" | "internal" | "observability" | None
    timestamp: float | None          # Event timestamp
```

## TUI Interface

### CogencyCode App
```python
from cogency_code import CogencyCode

# Launch TUI
app = CogencyCode(llm_provider="glm", conversation_id="session")
app.run()

# Programmatic query handling
async def handle_query(query: str):
    app = CogencyCode()
    await app.handle_query(query)
```

## Protocol Interfaces

### LLM Protocol
```python
class LLM(Protocol):
    async def stream(messages: list[dict]) -> AsyncGenerator[str, None]:
        """HTTP streaming with full context"""
        
    async def generate(messages: list[dict]) -> str:
        """One-shot completion"""
        
    # WebSocket session methods (optional)
    async def connect(messages: list[dict]) -> "LLM":
        """Create session with context"""
        
    async def send(content: str) -> AsyncGenerator[str, None]:
        """Send message in session"""
        
    async def close() -> None:
        """Close session"""
```

### Storage Protocol
```python
class Storage(Protocol):
    async def save_message(conversation_id, user_id, type, content, timestamp):
        """Save message to conversation"""
        
    async def load_messages(conversation_id, user_id, include, exclude):
        """Load conversation with filtering"""
        
    async def save_profile(user_id, profile):
        """Save user profile"""
        
    async def load_profile(user_id) -> dict:
        """Load user profile"""
        
    async def count_user_messages(user_id, since_timestamp):
        """Count messages for learning cadence"""
```

### Tool Protocol
```python
class Tool(ABC):
    name: str                    # Tool identifier
    description: str            # Tool description  
    schema: dict                # Parameter schema
    
    async def execute(**kwargs) -> ToolResult:
        """Execute tool with error handling"""
        
    def describe(args: dict) -> str:
        """Human-readable action description"""

class ToolResult:
    outcome: str                 # Natural language completion
    content: str | None         # Optional detailed data
    error: bool                 # True if execution failed
```

## Built-in Components

### LLM Providers
```python
# String identifiers
"openai"      # OpenAI (HTTP + WebSocket)
"anthropic"   # Anthropic (HTTP only)  
"gemini"      # Gemini (HTTP + WebSocket)

# Or pass instances directly
from cogency.lib.llms import OpenAI, Anthropic, Gemini
agent = Agent(llm=OpenAI(model="gpt-4o-mini"))
```

### Tools
```python
from cogency.tools import (
    # Code tools
    Create, Grep, Read, Replace, Shell, Tree,
    # Memory tools
    Recall,
    # Web tools
    Scrape, Search,
    # Tool registry
    tools  # Default tool collection
)
```

### Security Configuration
```python
class Security:
    access: "sandbox" | "project" | "system" = "sandbox"
    shell_timeout: int = 30      # Shell command timeout (seconds)
    api_timeout: float = 30.0    # HTTP/LLM call timeout
```

## Execution Modes

### **auto** (Default)
```python
# Try resume first, fallback to replay on failure
# Best for mixed workloads with WebSocket-capable LLMs
```

### **resume** (WebSocket)
```python
# Establish persistent session with LLM
# Tool injection without context rebuild
# Maximum token efficiency
# Requires LLM with WebSocket support
```

### **replay** (HTTP)
```python
# Stateless HTTP requests
# Context rebuilt each iteration
# Universal LLM compatibility
# Used by GLM, Anthropic, HTTP-only providers
```

## Usage Patterns

### Basic Streaming
```python
agent = Agent(llm="openai")
async for event in agent("What is 2+2?"):
    if event["type"] == "respond":
        print(event["content"])  # "4"
```

### Token Streaming
```python
async for event in agent("Explain AI", chunks=True):
    if event["type"] == "chunk":
        print(event["content"], end="")  # Raw tokens
```

### Tool Usage Monitoring
```python
async for event in agent("Read my file.txt"):
    if event["type"] == "call":
        print(f"Calling: {event['payload']['name']}")
    if event["type"] == "result": 
        print(f"Result: {event['content']}")
```

### Persistent Conversations
```python
agent = Agent(llm="openai")
async for event in agent(
    "Hello", 
    user_id="user123",
    conversation_id="chat456"
):
    # Automatically saved to storage
    print(event["content"])
```

### Complete Rendering Pipeline
```python
from cogency import Agent, Renderer

# Setup
app = CogencyCode(llm_provider="glm", debug=True)

# Execute queries
async def chat():
    queries = [
        "What files are in this directory?",
        "Read the main.py file", 
        "Summarize the code"
    ]
    
    for query in queries:
        print(f"\n🤖 Query: {query}")
        await app.handle_query(query)

# Run
asyncio.run(chat())
```

## Architecture Principles

### Design Purity
- **Immutability** - Frozen dataclass configuration prevents runtime drift
- **Protocol-based** - Clean interfaces enable perfect swapping
- **Single Responsibility** - Each component has one clear purpose
- **Explicit Configuration** - Constructor is the single configuration point
- **Type Safety** - Comprehensive typing with Protocol runtime checking

### Reference Grade Patterns
- **Honest Failures** - Storage raises on errors, no silent lies
- **Zero Ceremony** - `Agent(llm="openai")` just works
- **Clean Abstractions** - Events, protocols, modes are crystal clear
- **Resource Management** - Proper async context, session cleanup
- **Security Boundaries** - Access levels, timeouts, sandboxing

### Error Handling
```python
class AgentError(Exception):
    """Wraps execution errors without sensitive data leakage"""
    
# Automatic fallback in auto mode:
# resume failure → replay fallback
# Tool errors → handled by tool.execute()
# Storage errors → raised immediately (honest failures)
```

## Configuration Immutability

All configuration is frozen after construction:
```python
@dataclass(frozen=True)
class Config:
    # All settings immutable after Agent.__init__
    # Prevents runtime configuration drift
```

---

**Reference grade code that reads like English. Complete control with clean separation of concerns and type safety.**