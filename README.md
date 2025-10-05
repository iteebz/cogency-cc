# cogency-code

**A TUI coding agent built with cogency**

## Installation

```bash
poetry install
poetry run python -m cogency_code
```

## Vision

Minimal terminal interface that dogfoods cogency to build and improve itself.

## Extending the agent

The TUI intentionally keeps its agent factory fixed: `cogency_code.agent.create_agent` wires
in the standard identity, instructions, and security profile so every session behaves the
same way. If you need a custom pipeline, fork that function and swap in your own LLM,
security, or instructions—then point the Textual app at the new factory. Keeping the default
surface opinionated lets us evolve features deliberately while still leaving a clear hook for
experimentation.
