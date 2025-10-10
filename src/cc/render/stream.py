"""Renderer for cogency event streams.

Event symbols:
  $ - user input
  ~ - agent thinking
  ○ - tool call (in progress)
  ● - tool result (completed)
  > - agent response
  --- - turn separator
"""

import asyncio
import os
import time

from rich import print as rprint

from .color import C
from .diff import render_diff
from .format import format_call, format_result, tool_outcome


class Renderer:
    def __init__(
        self,
        verbose: bool = False,
        messages: list | None = None,
        llm=None,
        conv_id: str | None = None,
        config=None,
        evo_mode: bool = False,
    ):
        self.verbose = verbose
        self.messages = messages or []
        self.llm = llm
        self.conv_id = conv_id
        self.config = config
        self.evo_mode = evo_mode
        self.enable_rolling_summary = False

        self.state = None
        self.header_shown = False
        self.first_chunk = True
        self.pending_calls = {}
        self.spinner_tasks = {}
        self.thinking_task = None
        self.turn_start = None
        self.turn_events = []
        self.turn_tools = 0
        self.call_start_times = {}

    async def render_stream(self, stream):
        self.turn_start = time.time()

        try:
            async for event in stream:
                self.turn_events.append(event)

                if not self.header_shown:
                    self._render_header()
                    self.header_shown = True

                await self._render_event(event)
        except Exception as e:
            from cogency.lib.logger import logger

            logger.error(f"Stream error: {e}")
            print(f"\n{C.RED}✗ Stream error: {e}{C.R}")
            raise

    def _render_header(self):
        parts = []
        if self.messages:
            parts.append(f"{len(self.messages)} msgs")
            calls = sum(1 for m in self.messages if m.get("type") == "call")
            if calls:
                parts.append(f"{calls} calls")

            metrics = next(
                (
                    m["total"]
                    for m in reversed(self.messages)
                    if m.get("type") == "metric" and "total" in m
                ),
                None,
            )
            if metrics:
                total = metrics["input"] + metrics["output"]
                pct = int(total / 128000 * 100)
                parts.append(f"{metrics['input']}→{metrics['output']} tok ({pct}%)")

        if parts:
            print(f"{C.GRAY}» {' | '.join(parts)}{C.R}")

    async def _render_event(self, e):
        match e["type"]:
            case "user":
                if e["content"]:
                    print(f"{C.GRAY}---{C.R}\n{C.CYAN}${C.R} {e['content']}")
                    self.state = "user"
                    self.thinking_task = asyncio.create_task(self._think_spin())

            case "intent":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    print("\r\033[K", end="", flush=True)
                if e.get("content"):
                    print(f"{C.GRAY}intent: {e['content']}{C.R}")

            case "think":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    print("\r\033[K", end="", flush=True)
                if e["content"] and e["content"].strip():
                    if self.state != "think":
                        self._newline()
                        print(f"{C.GRAY}~{C.R} ", end="", flush=True)
                        self.state = "think"
                        self.first_chunk = True
                    content = e["content"].lstrip() if self.first_chunk else e["content"]
                    if self.first_chunk:
                        print(content, end="", flush=True)
                        self.first_chunk = False
                    else:
                        print(content, end="", flush=True)

            case "respond":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    print("\r\033[K", end="", flush=True)
                if e["content"] and e["content"].strip():
                    if self.state != "respond":
                        self._newline(force=True)
                        print(f"{C.MAGENTA}›{C.R} ", end="", flush=True)
                        self.state = "respond"
                        self.first_chunk = True
                    content = e["content"].lstrip() if self.first_chunk else e["content"]
                    self.first_chunk = False
                    rprint(content, end="", flush=True)

            case "call":
                from cogency.tools.parse import parse_tool_call

                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    print("\r\033[K", end="", flush=True)

                self._newline()
                self.state = None
                self.turn_tools += 1

                try:
                    call = parse_tool_call(e.get("content", ""))
                    key = self._call_key(call)
                    self.pending_calls[key] = call
                    print(f"{C.GRAY}○{C.R} {C.GRAY}{format_call(call)}{C.R}", end="", flush=True)
                except Exception:
                    if self.pending_calls:
                        last_key = list(self.pending_calls.keys())[-1]
                        del self.pending_calls[last_key]

            case "execute":
                if self.pending_calls:
                    # Spin for the last call added
                    last_key = list(self.pending_calls.keys())[-1]
                    self.call_start_times[last_key] = time.time()
                    self.spinner_tasks[last_key] = asyncio.create_task(
                        self._spin(self.pending_calls[last_key])
                    )

            case "result":
                # Cancel all spinner tasks
                for task in self.spinner_tasks.values():
                    task.cancel()
                self.spinner_tasks.clear()

                # Handle the result - try to match it with a pending call
                call_key = None
                if self.pending_calls:
                    # If we have pending calls, assume this result is for the most recent one
                    call_key = list(self.pending_calls.keys())[-1]
                    call = self.pending_calls.pop(call_key)
                    if start := self.call_start_times.pop(call_key, None):
                        time.time() - start

                    payload = e.get("payload", {})
                    outcome = format_result(call, payload)
                    is_error = payload.get("error", False)
                    symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
                    print(f"\r\033[K{symbol} {outcome}", flush=True)

                    content = payload.get("content")
                    if content and call.name == "edit":
                        for line in render_diff(content):
                            print(line)
                        print()
                    else:
                        print()

                    self.state = None
                else:
                    # No pending calls, display result directly
                    payload = e.get("payload", {})
                    outcome = tool_outcome(payload)
                    if outcome:
                        message = outcome
                    else:
                        message = payload.get("message", "ok")
                    is_error = e.get("payload", {}).get("error")
                    symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
                    print(f"\r\033[K{symbol} {message}\n", end="", flush=True)
                    self.state = None

            case "end":
                # Flush buffered results before ending
                if self.pending_calls:
                    for key in list(self.pending_calls.keys()):
                        self.call_start_times.pop(key, None)
                    self.pending_calls.clear()
                self._newline()
                print()
                await self._finalize()

            case "error":
                msg = e.get("payload", {}).get("error") or e.get("content", "Unknown error")
                print(f"{C.RED}✗{C.R} {msg}")

            case "interrupt":
                print(f"{C.YELLOW}⚠{C.R} Interrupted")

    async def _think_spin(self):
        if os.getenv("CI") == "true":
            return

        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                print(f"\r{C.GRAY}{frames[i]} thinking ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.08)
        except asyncio.CancelledError:
            pass

    async def _spin(self, call):
        if os.getenv("CI") == "true":
            return

        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                label = format_call(call).replace(": ...", "")
                print(f"\r{C.CYAN}{frames[i]} {label} ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.4)
        except asyncio.CancelledError:
            pass

    def _newline(self, force: bool = False):
        if force or self.state in ("think", "respond"):
            print()
        self.state = None

    def _call_key(self, call):
        # Return a hashable key for the call to distinguish concurrent calls
        return f"{call.name}::{str(call.args)}"

    def _render_diff(self, diff: str):
        if not diff.strip():
            print()
            return

        lines = diff.split("\n")
        for line in lines:
            if line.startswith("---") or line.startswith("+++"):
                print(f"{C.GRAY}{line}{C.R}")
            elif line.startswith("@@"):
                print(f"{C.CYAN}{line}{C.R}")
            elif line.startswith("+"):
                print(f"{C.GREEN}{line}{C.R}")
            elif line.startswith("-"):
                print(f"{C.RED}{line}{C.R}")
            else:
                print(line)
        print()

    async def _finalize(self):
        if not self.evo_mode:
            return

        if not (self.conv_id and self.llm and self.config):
            return

        await self._evo_compact()

    async def _evo_compact(self):
        import uuid

        from cogency.lib.compaction import maybe_cull
        from cogency.lib.logger import logger
        from cogency.lib.storage import SQLite, SummaryStorage

        msg_storage = SQLite()
        sum_storage = SummaryStorage()
        threshold = getattr(self.config, "compact_threshold", 10)

        culled = await maybe_cull(
            self.conv_id, "cogency", msg_storage, sum_storage, self.llm, threshold
        )

        if culled:
            new_id = str(uuid.uuid4())
            self.config.update(conversation_id=new_id)
            logger.debug(f"🔄 EVO: compacted → new conv {new_id[:8]}")
