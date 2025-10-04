# cogency-code vs cogency CLI

Purpose: document how the Textual TUI (`cogency-code`) and the Typer-powered CLI (`cogency`) overlap, diverge, and where they must stay in lock-step. This supports the batteries-included decision and keeps integration discussions grounded in facts.

## Surface Overview

| Capability | `cogency` CLI | `cogency-code` TUI |
|------------|---------------|--------------------|
| Interaction model | One-shot or multi-turn commands via Typer entry point `cogency run` with flags for provider, mode, user, conversation, and custom agent modules. | Persistent Textual app with header/stream/footer widgets; queries submitted through input bar with optional slash commands. |
| Streaming presentation | `Renderer.render_stream` prints events with `$/~ /○ /● />` markers and optional history header; metrics only when verbose. | `StreamView` renders events with Rich styling, header shows model/session/mode, footer tracks metrics and input focus. |
| Session boot | Stateless by default; multi-turn via `--conv`. | Auto-generates conversation IDs, supports resume picker modal when launched in resume-selection mode, and slash `/clear` for new sessions. |
| Configuration | CLI flags per run; environment variables for API keys; `--agent` loads external Agent factory. | Persisted config in `~/.cogency-code/config.json`; modal config panel updates API keys, provider, mode, identity without restart. |
| Diagnostics | Subcommands: `context`, `conv`, `stats`, `users`, `nuke`. | `/docs` slash command points back to the base CLI diagnostics. |
| Conversation hygiene | Manual via CLI (nuke, context). | Slash `/compact` summarizes prior session and rolls into new ID. |
| Extensibility | `--agent` flag swaps implementation; renderer importable for custom shells. | Hard-wired to `create_agent` factory; identity/provider configurable via panel; no external agent injection today. |
| Input ergonomics | Plain terminal line output; rely on shell history. | Visual event stream, keyboard shortcuts (`ctrl+l`, `ctrl+g`, double `ctrl+c`) and resume modal. |

## Key References

- `public/cogency/src/cogency/cli/__init__.py` — command entry, flags, diagnostic subcommands.
- `public/cogency/src/cogency/cli/display.py` — streaming renderer and event framing.
- `public/cogency-code/src/cogency_code/app.py` — Textual layout, bindings, resume picker, metrics update, config flow.
- `public/cogency-code/src/cogency_code/widgets/footer.py` — query vs slash command routing.
- `public/cogency-code/src/cogency_code/commands.py` — `/clear` and `/compact` handlers.

## Parity Checkpoints

1. **One-shot semantics** — Both surfaces must answer direct questions without greeting loops. Recent fixes landed in the TUI; confirm the Typer path (`run_agent`) emits responses without extra ceremony.
2. **Streaming markers** — Ensure event symbol mapping stays consistent between renderer and Textual view so logs match screenshots and docs.
3. **Metrics surfacing** — TUI currently updates metrics in the header after a turn, while CLI hides them unless `verbose`. Decide whether to expose parity (either always-on in both or consistently optional).
4. **Configuration breadth** — CLI allows external agent modules; TUI does not. If we keep both, document why and whether a TUI hook is needed.
5. **Diagnostics coverage** — TUI lacks equivalents for `context`, `stats`, `users`, and `nuke`. Either add slash/shortcut bindings or point operators back to the base CLI workflows.

## Decision Inputs

- If we merge surfaces, the comparison above highlights features we must preserve (resume picker, slash commands, diagnostics suite).
- If we keep them separate, publish positioning: CLI for scripting/ops, TUI for live coding dogfooding, with explicit guidance on when to use the base diagnostics shell.

Maintain this matrix as features evolve so batteries-included messaging reflects reality.

## Recommendations

- Integration test `public/cogency/tests/integration/test_cli_one_shot.py` now guards the one-shot path by invoking the Typer CLI with a stub agent and asserting the first output is the direct answer.
- Expose diagnostics parity by either binding slash commands (`/context`, `/stats`, `/users`) in the TUI that proxy to the underlying storage helpers or explicitly documenting in-app how to invoke the CLI diagnostics when needed.
- Close the extensibility gap by accepting an optional plugin path in `cogency_code.agent.create_agent` (similar to `--agent`) or publishing guidance on why the TUI intentionally omits that escape hatch.
