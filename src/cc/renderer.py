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
        enable_rolling_summary: bool = True,
        rolling_summary_threshold: int = 10,
    ):
        self.verbose = verbose
        self.messages = messages or []
        self.summaries = summaries or []
        self.llm = llm
        self.conv_id = conv_id
        self.config = config
        self.evo_mode = evo_mode
        self.enable_rolling_summary = enable_rolling_summary
        self.rolling_summary_threshold = rolling_summary_threshold

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
            print(f"\n{C.RED}✗ Stream error: {e}{C.R}")
            raise

    def _render_header(self):
        if self.summaries:
            print(f"{C.GRAY}context:{C.R}")
            for s in self.summaries:
                print(f"{C.GRAY}  {s['summary']}{C.R}")
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
                        print(f"{C.MAGENTA}>{C.R} ", end="", flush=True)
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
                    print(f"{C.CYAN}○{C.R} {self._fmt_call(call)}", end="", flush=True)
                except Exception:
                    # Remove last call on exception
                    if self.pending_calls:
                        last_key = list(self.pending_calls.keys())[-1]
                        del self.pending_calls[last_key]

            case "execute":
                if self.pending_calls:
                    # Spin for the last call added
                    last_key = list(self.pending_calls.keys())[-1]
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
                    call = self.pending_calls[call_key]

                    # Buffer the result for later processing
                    if call_key not in self.result_buffers:
                        self.result_buffers[call_key] = []
                    self.result_buffers[call_key].append(e)
                else:
                    # No pending calls, display result directly
                    outcome = self._fmt_result(None, e)
                    is_error = e.get("payload", {}).get("error")
                    symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
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
                            symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
                            print(f"\r\033[K{symbol} {outcome}\n", end="", flush=True)
                        del self.pending_calls[key]
                        del self.result_buffers[key]
                self._newline()
                print()
                await self._finalize()
                await self._rolling_summary()

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
                name = self._tool_name(call.name)
                print(f"\r{C.CYAN}{frames[i]} {name} ({elapsed}s){C.R}", end="", flush=True)
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
        return name

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

    async def _rolling_summary(self):
        """Generate rolling summary after each message completion."""
        if not self.conv_id or not self.llm or not self.enable_rolling_summary:
            return

        try:
            from cogency.lib.storage import SQLite

            from .storage import SummaryStorage

            msg_storage = SQLite()
            sum_storage = SummaryStorage()
            llm = self.llm

            if not llm:
                return

            # Get recent messages since last summary
            msgs = await msg_storage.load_messages(self.conv_id, "cogency")
            summaries = await sum_storage.load_summaries(self.conv_id)

            # Determine cutoff timestamp (last summary end or start of conversation)
            cutoff_ts = summaries[-1]["end"] if summaries else msgs[0].get("timestamp", 0)

            # Filter messages since last summary
            recent_msgs = [m for m in msgs if m.get("timestamp", 0) > cutoff_ts]

            # Only summarize if we have enough new messages
            if len(recent_msgs) < self.rolling_summary_threshold:
                return

            # Generate summary
            await self._generate_and_save_summary(recent_msgs, sum_storage, cutoff_ts)

        except Exception as e:
            from cogency.lib.logger import logger

            logger.debug(f"Rolling summary failed: {e}")

    async def _generate_and_save_summary(self, messages: list[dict], sum_storage, cutoff_ts: float):
        """Generate and save a summary for the given messages."""
        import time

        try:
            # Format messages for summarization
            formatted_msgs = []
            for m in messages:
                t = m.get("type", "unknown")
                content = m.get("content", "")[:200]  # Truncate for context
                if content and t in ["user", "respond", "think"]:
                    formatted_msgs.append(f"[{t}] {content}")

            if not formatted_msgs:
                return

            # Generate summary using LLM
            prompt = f"""Summarize this conversation excerpt in 1-2 concise sentences:

{chr(10).join(formatted_msgs)}

Focus on key actions, decisions, and outcomes. Be factual and brief."""

            result = await asyncio.wait_for(
                self.llm.generate([{"role": "user", "content": prompt}]), timeout=15.0
            )

            if not result:
                return

            summary = result.strip()
            if not summary:
                return

            # Save summary
            start_ts = messages[0].get("timestamp", time.time())
            end_ts = messages[-1].get("timestamp", time.time())

            await sum_storage.save_summary(
                self.conv_id, "cogency", summary, len(messages), start_ts, end_ts
            )

            from cogency.lib.logger import logger

            logger.debug(f"📝 Rolling summary: {len(messages)} msgs summarized")

        except asyncio.TimeoutError:
            from cogency.lib.logger import logger

            logger.debug("Rolling summary generation timed out")
        except Exception as e:
            from cogency.lib.logger import logger

            logger.debug(f"Rolling summary generation failed: {e}")

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
        threshold = 10  # Or some other appropriate value

        culled = await maybe_cull(
            self.conv_id, "cogency", msg_storage, sum_storage, self.llm, threshold
        )

        if culled:
            new_id = str(uuid.uuid4())
            self.config.update(conversation_id=new_id)
            logger.debug(f"🔄 EVO: compacted → new conv {new_id[:8]}")
