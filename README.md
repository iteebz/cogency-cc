# cogency-cc

Terminal UI for cogency agents. Stream events, persist conversations, execute code (project-scoped).

## Usage

```bash
poetry install
poetry run cc "What's in main.py?"           # Single query
poetry run cc                                 # Interactive (saves to ~/.cogency/)
poetry run cc --model claude "Debug this"    # Model selection (claude/gpt4/gemini)
```

## Configuration

**API keys** (env override, then `~/.cogency/cc.json`):
```bash
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."
export GEMINI_API_KEY="..."
```

**Project config** (`.cogency/cc.json`, committed):
```json
{
  "provider": "anthropic",
  "model": "claude-opus-4-1"
}
```

**Commands**:
```bash
cc session list / delete / export / resume <id>
cc profile show / clear
cc context show / set "prompt"
cc config show / --set-key <provider> <key>
```

## Rendering

```
$ What's in main.py?
~ I need to read the file

read("main.py")
✓ Found 50 lines
The file contains a Flask app...
───
Input: 120  Output: 80  Duration: 1.2s
```

Prefixes: `$` user (cyan), `~` think (gray), `✓` success (green), `✗` error (red).

## Architecture

- **Event stream** from cogency core → dispatch → render
- **State machine** phases (idle → user → think → call → result → respond → end)
- **Buffer** accumulates response until newline (markdown detection)
- **Persistence** SQLite at `~/.cogency/`
- **Security** cogency core enforces (file access, tool validation)

See [docs/](docs/) for details.

## Development

```bash
poetry run pytest
just build
```

## License

Apache 2.0
