# GLM + Cogency Integration Guide

**Complete reference for implementing and using GLM with cogency.**

## Quick Start

```python
from cogency_code import GLMAgent

# Agent with GLM provider
agent = GLMAgent()

# Stream responses
async for event in agent("What is 2+2?"):
    if event["type"] == "respond":
        print(event["content"])  # "4"
```

## Implementation Files

```
src/cogency_code/
├── llms/
│   └── glm.py          # GLM provider (LLM protocol)
├── agent.py            # Agent wrapper  
├── __main__.py         # Demo/testing
└── __init__.py         # Package exports
```

## Core GLM Provider

```python
# src/cogency_code/llms/glm.py
class GLM:
    async def stream(messages: list[dict]) -> AsyncGenerator[str, None]:
        """HTTP streaming with full context"""
        
    async def generate(messages: list[dict]) -> str:
        """One-shot completion"""
```

### Critical Implementation Details

```python
# GLM uses coding endpoint
CODING_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"

# Standard headers
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Request format
payload = {
    "model": "glm-4.5",
    "messages": messages,
    "stream": True
}
```

## Agent Wrapper

```python
# src/cogency_code/agent.py  
class GLMAgent:
    def __init__(self, **kwargs):
        self.agent = Agent(llm=GLM(), **kwargs)
    
    async def run(self, query: str, **kwargs) -> str:
        """Execute query, return final response"""
        
    async def stream(self, query: str, **kwargs):
        """Stream full event pipeline"""
```

## Environment Setup

```bash
# .env file
GLM_API_KEY=your_api_key_here
```

## Usage Patterns

### Basic Agent Usage
```python
from cogency_code import GLMAgent

agent = GLMAgent()

# Simple query
response = await agent.run("What is the capital of France?")
# Returns: "The capital of France is Paris"

# Full event stream
async for event in agent.stream("List files in current directory"):
    if event["type"] == "call":
        print(f"Tool: {event['content']}")
    elif event["type"] == "respond":
        print(f"Answer: {event['content']}")
```

### With Renderer (Visual Output)
```python
from cogency import Renderer
from cogency_code import GLMAgent

agent = GLMAgent()
renderer = Renderer()

# Visual terminal output
stream = agent.stream("What files are in this project?")
await renderer.render_stream(stream)

# Visual indicators:
# ~   LLM thinking
# ○   Tool call initiation  
# ●   Tool result
# >   Agent response
# %   Metrics/timing
```

### Tool Integration
GLM agent has access to standard cogency tools:

```python
# Available tools:
from cogency.tools import (
    FileRead, FileWrite, FileEdit,    # File operations
    FileList, FileSearch,             # File discovery
    MemoryRecall,                     # Memory search
    SystemShell,                      # Command execution
    WebSearch, WebScrape,             # Web operations
)

# Example: File operations
async for event in agent.stream("Read README.md and summarize"):
    # GLM will automatically use FileRead tool
    pass
```

### Configuration Options
```python
agent = GLMAgent(
    max_iterations=10,           # Max execution loops
    history_window=100,          # Context messages
    security=Security(           # Access control
        access="sandbox" | "project" | "system"
    ),
    debug=True                   # Verbose logging
)
```

## Protocol Compliance

GLM implements cogency's LLM protocol:

```python
class LLM(Protocol):
    async def stream(messages: list[dict]) -> AsyncGenerator[str, None]:
        """HTTP streaming with full context"""
        
    async def generate(messages: list[dict]) -> str:
        """One-shot completion"""
```

**GLM Implementation Details:**
- HTTP streaming only (no WebSocket support)
- Uses coding endpoint for better code understanding
- Proper error handling and session management
- Handles cogency event delimiters correctly
- Session reuse with aiohttp

## Execution Mode

GLM uses `replay` mode (HTTP only):

```python
agent = Agent(llm=GLM(), mode="replay")  # Explicit
agent = Agent(llm=GLM())                 # Auto-selects replay
```

**Characteristics:**
- Stateless HTTP requests
- Context rebuilt each iteration
- Universal LLM compatibility
- Automatic fallback selection

## Error Handling

```python
# GLM provider handles:
# - Network timeouts
# - API rate limits  
# - Invalid responses
# - Session cleanup

# Agent wrapper handles:
# - Tool execution failures
# - Storage errors (honest failures)
# - Context assembly issues
```

## Testing Your GLM Integration

```python
# Basic connectivity test
agent = GLMAgent()
response = await agent.run("What is 2+2?")
assert response == "4"

# Tool usage test  
response = await agent.run("What files are in current directory?")
assert len(response) > 0

# Streaming test
events = list(agent.stream("Hello"))
assert any(e["type"] == "respond" for e in events)
```

## Package Exports

```python
# src/cogency_code/__init__.py
from .agent import GLMAgent
from .llms.glm import GLM

__all__ = ["GLMAgent", "GLM"]
```

## Production Deployment

- GLM uses HTTP streaming (replay mode)
- Automatic context rebuild each iteration
- Session management built into provider
- Compatible with all cogency tools and features

---

**This is all you need to implement and use GLM with cogency. Everything else is implementation detail.**