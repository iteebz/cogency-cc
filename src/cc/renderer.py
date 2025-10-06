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
import time

from .lib.color import C


class Renderer:
    def __init__(
        self,
        verbose: bool = False,
        messages: list | None = None,
        llm=None,
        conv_id: str | None = None,
        summaries: list | None = None,
        config=None,
        evo_mode: bool = False,
    ):
        self.verbose = verbose
        self.messages = messages or []
        self.summaries = summaries or []
        self.llm = llm
        self.conv_id = conv_id
        self.config = config
        self.evo_mode = evo_mode

        self.state = None
        self.header_shown = False
        self.first_chunk = True
        self.pending_calls = {}
        self.result_buffers = {}
        self.spinner_tasks = {}
        self.thinking_task = None
        self.turn_start = None
        self.turn_events = []
        self.turn_tools = 0

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
            print(f"\n{C.red}✗ Stream error: {e}{C.R}")
            raise

    def _render_header(self):
        if self.summaries:
            print(f"{C.gray}context:{C.R}")
            for s in self.summaries:
                print(f"{C.gray}  {s['summary']}{C.R}")
            print()

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
            print(f"{C.gray}» {' | '.join(parts)}{C.R}")

    async def _render_event(self, e):
        match e["type"]:
            case "user":
                if e["content"]:
                    print(f"{C.gray}---{C.R}\n{C.cyan}${C.R} {e['content']}")
                    self.state = "user"
                    self.thinking_task = asyncio.create_task(self._think_spin())

            case "intent":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    print("\r\033[K", end="", flush=True)
                if e.get("content"):
                    print(f"{C.gray}intent: {e['content']}{C.R}")

            case "think":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    print("\r\033[K", end="", flush=True)
                if e["content"] and e["content"].strip():
                    if self.state != "think":
                        self._newline()
                        print(f"{C.gray}~{C.R} ", end="", flush=True)
                        self.state = "think"
                        self.first_chunk = True
                    content = e["content"].lstrip() if self.first_chunk else e["content"]
                    self.first_chunk = False
                    print(content, end="", flush=True)

            case "respond":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    print("\r\033[K", end="", flush=True)
                if e["content"] and e["content"].strip():
                    if self.state != "respond":
                        self._newline()
                        print(f"{C.magenta}>{C.R} ", end="", flush=True)
                        self.state = "respond"
                        self.first_chunk = True
                    content = e["content"].lstrip() if self.first_chunk else e["content"]
                    self.first_chunk = False
                    print(content, end="", flush=True)

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
                    self.result_buffers[key] = []
                    print(f"{C.cyan}○{C.R} {self._fmt_call(call)}", end="", flush=True)
                except Exception:
                    # Remove last call on exception
                    if self.pending_calls:
                        last_key = list(self.pending_calls.keys())[-1]
                        del self.pending_calls[last_key]

            case "execute":
                if self.pending_calls:
                    # Spin for the last call added
                    last_key = list(self.pending_calls.keys())[-1]
                    self.spinner_task = asyncio.create_task(self._spin(self.pending_calls[last_key]))

            case "result":
                if self.spinner_task:
                    self.spinner_task.cancel()
                    self.spinner_task = None

                if self.pending_call:
                    if not hasattr(self, "result_buffer"):
                        self.result_buffer = []
                    self.result_buffer.append(e)
                else:
                    outcome = self._fmt_result(None, e)
                    is_error = e.get("payload", {}).get("error", False)
                    symbol = f"{C.red}✗{C.R}" if is_error else f"{C.green}●{C.R}"
                    print(f"\r\033[K{symbol} {outcome}\n", end="", flush=True)
                    self.state = None

            case "end":
                # Flush buffered results before ending
                if self.pending_calls:
                    for key in list(self.pending_calls.keys()):
                        for buffered_event in self.result_buffers.get(key, []):
                            call = self.pending_calls.get(key)
                            outcome = self._fmt_result(call, buffered_event)
                            is_error = buffered_event.get("payload", {}).get("error", False)
                            symbol = f"{C.red}✗{C.R}" if is_error else f"{C.green}●{C.R}"
                            print(f"\r\033[K{symbol} {outcome}\n", end="", flush=True)
                        del self.pending_calls[key]
                        del self.result_buffers[key]
                self._newline()
                print()

            case "end":
                self._newline()
                print()
                await self._finalize()

            case "error":
                msg = e.get("payload", {}).get("error") or e.get("content", "Unknown error")
                print(f"{C.red}✗{C.R} {msg}")

            case "interrupt":
                print(f"{C.yellow}⚠{C.R} Interrupted")

    async def _think_spin(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                print(f"\r{C.gray}{frames[i]} thinking ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.08)
        except asyncio.CancelledError:
            pass

    async def _spin(self, call):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                name = self._tool_name(call.name)
                print(f"\r{C.cyan}{frames[i]} {name} ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.4)
        except asyncio.CancelledError:
            pass

    def _newline(self):
        if self.state in ("think", "respond"):
            print()
        self.state = None

    def _fmt_call(self, call) -> str:
        name = self._tool_name(call.name)
        arg = self._tool_arg(call.args)
        return f"{name}({arg}): ..." if arg else f"{name}(): ..."

    def _fmt_result(self, call, event) -> str:
        name = self._tool_name(call.name)
        arg = self._tool_arg(call.args)
        outcome = self._tool_outcome(event.get("payload", {}))
        base = f"{name}({arg})" if arg else f"{name}()"
        return f"{base}: {outcome}"

    def _tool_name(self, name: str) -> str:
        import re

        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def _tool_arg(self, args: dict) -> str:
        if not isinstance(args, dict):
            return ""

        for k in ["file", "path", "file_path", "pattern", "query", "command", "url", "dir"]:
            if v := args.get(k):
                s = str(v)
                return s if len(s) < 50 else s[:47] + "..."

        if args:
            s = str(next(iter(args.values())))
            return s if len(s) < 50 else s[:47] + "..."
        return ""

    def _tool_outcome(self, payload: dict) -> str:
        if payload.get("error"):
            return payload.get("outcome", "error")

        outcome = payload.get("outcome", "")

        if outcome.startswith("LOC "):
            parts = outcome[4:].split()
            if len(parts) == 2:
                return f"+{parts[0]}/-{parts[1]}"

        if outcome.startswith("Listed ") and " items" in outcome:
            return f"{outcome.split()[1]} items"

        if outcome.startswith("Found "):
            if " matches" in outcome:
                return f"{outcome.split()[1]} matches"
            if " results" in outcome:
                return f"{outcome.split()[1]} results"

        return outcome or "ok"

    def _call_key(self, call):
        # Return a hashable key for the call to distinguish concurrent calls
        return f"{call.name}::{str(call.args)}"

    async def _finalize(self):
        if not self.evo_mode:
            return

        if not (self.conv_id and self.llm and self.config):
            return

        asyncio.create_task(self._evo_compact())

    async def _evo_compact(self):
        try:
            import uuid

            from cogency.lib.logger import logger
            from cogency.lib.storage import SQLite

            from .compact import maybe_cull
            from .storage import SummaryStorage

            msg_storage = SQLite()
            sum_storage = SummaryStorage()
            threshold = self.config.compact_threshold

            culled = await maybe_cull(
                self.conv_id, "cogency", msg_storage, sum_storage, self.llm, threshold
            )

            if culled:
                new_id = str(uuid.uuid4())
                self.config.update(conversation_id=new_id)
                logger.debug(f"🔄 EVO: compacted → new conv {new_id[:8]}")
        except Exception as e:
            from cogency.lib.logger import logger

            logger.debug(f"Evo compact failed: {e}")
