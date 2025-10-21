"""Context inspection for conversations."""

import json

import typer

from ..config import Config
from ..conversations import get_last_conversation
from ..lib.fs import root
from ..lib.sqlite import Snapshots
from ..render.color import C


async def show_context(config: Config, snapshots: Snapshots):
    project_root = root()
    if not project_root:
        typer.echo("No project root found")
        return

    conv_id = config.conversation_id
    if not conv_id:
        conv_id = get_last_conversation(str(project_root))

    if not conv_id:
        typer.echo("No conversation found")
        return

    from ..lib.sqlite import storage as get_storage

    storage = get_storage(config)
    msgs = await storage.load_messages(conv_id, config.user_id)

    if not msgs:
        typer.echo("No messages in conversation")
        return

    dist = {}
    latest_metric = None

    for m in msgs:
        t = m.get("type", "unknown")
        dist[t] = dist.get(t, 0) + 1
        if t == "metric" and "total" in m:
            latest_metric = m["total"]

    debug = config.debug_mode  # Assuming debug_mode is set in Config

    typer.echo(f"{C.gray}conversation: {conv_id[:8]}{C.R}")
    typer.echo(f"{C.gray}messages: {len(msgs)}{C.R}")
    typer.echo(f"{C.gray}distribution:{C.R}")
    for t, count in sorted(dist.items(), key=lambda x: -x[1]):
        pct = int(count / len(msgs) * 100)
        typer.echo(f"  {t}: {count} ({pct}%)")

    if latest_metric:
        total = latest_metric.get("input", 0) + latest_metric.get("output", 0)
        typer.echo(
            f"{C.gray}tokens: {latest_metric.get('input', 0)}→{latest_metric.get('output', 0)} ({total:,} total){C.R}"
        )
    else:
        est_tokens = sum(len(m.get("content", "")) // 4 for m in msgs)
        typer.echo(f"{C.gray}estimated tokens: ~{est_tokens:,}{C.R}")
    typer.echo()

    if not debug:
        typer.echo(f"{C.gray}use --debug to see full messages{C.R}")
        return

    for i, msg in enumerate(msgs):
        msg_type = msg.get("type", "unknown")
        msg.get("role", "")
        content = msg.get("content", "")

        if msg_type == "user":
            typer.echo(f"{C.cyan}[{i}] user{C.R}")
            typer.echo(f"{content}\n")

        elif msg_type == "assistant":
            typer.echo(f"{C.magenta}[{i}] assistant{C.R}")
            typer.echo(f"{content}\n")

        elif msg_type == "system":
            typer.echo(f"{C.gray}[{i}] system{C.R}")
            preview = content[:100] + "..." if len(content) > 100 else content
            typer.echo(f"{preview}\n")

        elif msg_type == "call":
            typer.echo(f"{C.cyan}[{i}] call{C.R}")
            try:
                call_data = json.loads(content) if isinstance(content, str) else content
                typer.echo(f"{json.dumps(call_data, indent=2)}\n")
            except Exception:
                typer.echo(f"{content}\n")

        elif msg_type == "result":
            typer.echo(f"{C.green}[{i}] result{C.R}")
            payload = msg.get("payload", {})
            if payload:
                typer.echo(f"{json.dumps(payload, indent=2)}\n")
            else:
                typer.echo(f"{content}\n")

        elif msg_type == "summary":
            typer.echo(f"{C.gray}[{i}] summary{C.R}")
            summary_data = msg.get("summary", content)
            typer.echo(f"{summary_data}\n")

        elif msg_type == "metric":
            total_data = msg.get("total", {})
            window_data = msg.get("window", {})
            typer.echo(f"{C.gray}[{i}] metric{C.R}")
            if total_data:
                typer.echo(
                    f"  total: {total_data.get('input', 0)}→{total_data.get('output', 0)} tok"
                )
            if window_data:
                typer.echo(
                    f"  window: {window_data.get('input', 0)}→{window_data.get('output', 0)} tok"
                )
            typer.echo()
