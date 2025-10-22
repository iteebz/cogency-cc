# cogency-cc

**Streaming coding CLI for [cogency](https://github.com/iteebz/cogency) agents.**

Stream events from the agent event loop. Persist conversations to SQLite. Execute code with project-scoped sandboxing. No bloat. No configuration hell. Just clean.

**[Architecture](docs/architecture.md)** | **[Design](docs/design.md)** | **[Protocol](docs/protocol.md)**

## Install

```bash
pip install cogency-cc
```

or from source:

```bash
git clone https://github.com/iteebz/cogency-cc
cd cogency-cc
poetry install
poetry run cc "What's in main.py?"
```

## Usage

```bash
# Interactive (learns your style)
cc

# One-shot query
cc "What's in main.py?"

# Model selection (overrides config)
cc --model claude "Debug this"
cc --model gpt4 "Code review"
cc --model gemini "Generate tests"
```

**Commands:**
```bash
cc session list / resume <id> / delete <id> / export <id>
cc profile show / clear
cc context show / set "prompt"
cc config show / --set-key <provider> <key>
```

## Configuration

API keys (precedence):
1. Environment: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`
2. Project: `.cogency/cc.json` (shared, committed)
3. Home: `~/.cogency/cc.json` (personal)

**Example `.cogency/cc.json`:**
```json
{
  "provider": "anthropic",
  "model": "claude-opus-4-1"
}
```

**Model aliases:**
```
claude  → anthropic/claude-opus-4-1
gpt4    → openai/gpt-4o
gemini  → gemini/gemini-2.0-flash-001
```

## Output Format

```
$ What's in main.py?
~ I need to read it

read("main.py")
✓ Found 50 lines
The file has a Flask app...
───
Input: 120  Output: 80
```

Prefixes: `$` cyan (query), `~` gray (think), `✓` green (success), `✗` red (error), `───` separator.

Features: markdown rendering, incremental streaming, token metrics, session resume.

## Architecture

**Stateless, event-driven:**
- cogency core sends events
- Renderer dispatches → state machine → buffer → formatter → terminal
- Same events + config = identical output (crash-safe)
- Conversations persisted (SQLite at `~/.cogency/`)
- Security enforced by cogency core (file access, sandbox)

See **[docs/architecture.md](docs/architecture.md)** for the full pipeline.

## Development

```bash
just build          # Format, lint, test
poetry run pytest   # All tests
poetry run ruff check src tests
```

## Status

**Alpha** (v0.1.0). Core stable. API may evolve with cogency.

## License

Apache 2.0

**See [cogency](https://github.com/iteebz/cogency) for the agent framework. See [docs/](docs/) for protocol, design principles, and security model.**
