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
import re
import time

from .color import C
from .diff import render_diff
from .format import format_call, format_result, tool_outcome


def render_markdown(text: str) -> str:
    """Render markdown with ANSI codes."""
    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", f"{C.BOLD}\\1{C.R}", text)

    # Italic: *text* (but not list markers)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)", "\033[3m\\1\033[0m", text)

    # Inline code: `code`
    text = re.sub(r"`([^`]+)`", f"{C.GRAY}\\1{C.R}", text)

    # Headers: # text
    text = re.sub(r"^(#{1,6})\s+(.+)$", f"{C.BOLD}{C.CYAN}\\2{C.R}", text, flags=re.MULTILINE)

    # Links: [text](url) → text (url)
    return re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", f"{C.CYAN}\\1{C.R} {C.GRAY}(\\2){C.R}", text)


def is_markdown_content(text: str) -> bool:
    """Check if text contains markdown patterns."""
    markdown_patterns = [
        r"^#{1,6}\s+",
        r"\*\*.*?\*\*",
        r"`[^`]+`",
        r"\[.*?\]\(.*?\)",
    ]

    return any(re.search(pattern, text, re.MULTILINE) for pattern in markdown_patterns)


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
        self.turn_tools = 0
        self.call_start_times = {}
        self.newline_buffer = ""
        self._last_char_newline = True  # New attribute

    async def render_stream(self, stream):
        self.turn_start = time.time()

        try:
            async for event in stream:
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

        # Get latest token count from metrics
        token_part = None
        latest_metric = next(
            (m for m in reversed(self.messages) if m.get("type") == "metric"), None
        )
        if latest_metric and "total" in latest_metric:
            total = latest_metric["total"]
            total_tokens = total.get("input", 0) + total.get("output", 0)
            token_part = f"{total_tokens / 1000:.1f}k tokens"

        # Count messages
        msg_count = len(self.messages) if self.messages else 0
        msg_part = f"{msg_count} msgs"

        # Count tools
        tools_count = sum(1 for m in self.messages if m.get("type") == "call")
        tool_part = f"{tools_count} tools"

        # Get model name (default to glm-4.6)
        model_name = "glm-4.6"
        if self.config and hasattr(self.config, "model") and self.config.model:
            model_name = self.config.model
        elif self.config and hasattr(self.config, "provider") and self.config.provider:
            model_name = self.config.provider

        parts = []
        if token_part:
            parts.append(token_part)
        parts.append(msg_part)
        parts.append(tool_part)
        parts.append(model_name)

        if parts:
            self._print(f"{C.GRAY}{' · '.join(parts)}{C.R}")

    async def _render_event(self, e):
        match e["type"]:
            case "user":
                if e["content"]:
                    self._print(f"{C.GRAY}---{C.R}\n{C.CYAN}${C.R} {e['content']}")
                    self.state = "user"
                    self.thinking_task = asyncio.create_task(self._think_spin())

            case "intent":
                # Cancel spinner for intent events
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    self._print("\r\033[K", end="", flush=True)
                if e.get("content"):
                    self._print(f"{C.GRAY}intent: {e['content']}{C.R}")

            case "think":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    self._print("\r\033[K", end="", flush=True)
                if e["content"] and e["content"].strip():
                    if self.state != "think":
                        self._newline()
                        self._print(f"{C.GRAY}~{C.R} ", end="", flush=True)
                        self.state = "think"
                        self.first_chunk = True
                    content = e["content"].lstrip() if self.first_chunk else e["content"]
                    if self.first_chunk:
                        self._print(f"{C.GRAY}{content}{C.R}", end="", flush=True)
                        self.first_chunk = False
                    else:
                        self._print(f"{C.GRAY}{content}{C.R}", end="", flush=True)

            case "respond":
                # Don't cancel spinner immediately - wait for real content
                has_real_content = e["content"] and e["content"].strip()

                if has_real_content and self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    self._print("\r\033[K", end="", flush=True)

                if not e["content"]:
                    return

                content = e["content"]

                # State transition: delay until we have real content
                if self.state != "respond":
                    if content.strip():
                        # Only add newline if we're not at the start of a new line
                        if not self._last_char_newline:
                            self._newline()
                        self._print(f"{C.MAGENTA}›{C.R} ", end="", flush=True)
                        self.state = "respond"
                        self.first_chunk = False
                        self._print(content.lstrip(), end="", flush=True)
                    else:
                        # Buffer whitespace until real content
                        self.newline_buffer += content
                    return

                # Already in respond state
                if content.strip():
                    # Real content - flush buffer then print
                    if self.newline_buffer:
                        self._print(self.newline_buffer, end="", flush=True)
                        self.newline_buffer = ""
                    self._print(content, end="", flush=True)
                else:
                    # Trailing whitespace - buffer it
                    self.newline_buffer += content

            case "call":
                from cogency.tools.parse import parse_tool_call

                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    self._print("\r\033[K", end="", flush=True)

                self.newline_buffer = ""
                self._newline()
                self.state = None
                self.turn_tools += 1

                try:
                    call = parse_tool_call(e.get("content", ""))
                    key = self._call_key(call)
                    self.pending_calls[key] = call
                    self._print(
                        f"{C.GRAY}○{C.R} {C.GRAY}{format_call(call)}{C.R}", end="", flush=True
                    )
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
                    self._print(f"\r\033[K{symbol} {outcome}", flush=True)

                    content = payload.get("content")
                    if content and call.name == "edit":
                        for line in render_diff(content):
                            self._print(line)
                    # Removed the else branch that printed a newline

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
                    self._print(f"\r\033[K{symbol} {message}\n", end="", flush=True)
                    self.state = None

            case "end":
                # Flush buffered results before ending
                if self.pending_calls:
                    for key in list(self.pending_calls.keys()):
                        self.call_start_times.pop(key, None)
                    self.pending_calls.clear()
                self._newline()
                self._print()
                await self._finalize()

            case "error":
                msg = e.get("payload", {}).get("error") or e.get("content", "Unknown error")
                self._print(f"{C.RED}✗{C.R} {msg}")

            case "interrupt":
                self._print(f"{C.YELLOW}⚠{C.R} Interrupted")

    async def _think_spin(self):
        if os.getenv("CI") == "true":
            return

        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                self._print(f"\r{C.GRAY}{frames[i]} thinking ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.016)
        except asyncio.CancelledError:
            pass

    async def _spin(self, call):
        if os.getenv("CI") == "true":
            return

        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        label = format_call(call).replace(": ...", "")
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                self._print(f"\r{C.CYAN}{frames[i]} {label} ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.016)
        except asyncio.CancelledError:
            pass

    def _print(self, *args, **kwargs):
        # Determine the actual 'end' character that print() will use
        actual_end = kwargs.get("end", "\n")
        print(*args, **kwargs)
        self._last_char_newline = actual_end == "\n"

    def _newline(self, force: bool = False):
        # Only add newline if not transitioning to respond state
        if (force or self.state in ("think", "respond")) and not self._last_char_newline:
            self._print()

    def _call_key(self, call):
        # Return a hashable key for the call to distinguish concurrent calls
        return f"{call.name}::{str(call.args)}"

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
