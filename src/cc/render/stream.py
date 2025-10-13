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
        latest_metric: dict | None = None,
    ):
        self.verbose = verbose
        self.messages = messages or []
        self.llm = llm
        self.conv_id = conv_id
        self.config = config
        self.evo_mode = evo_mode
        self.latest_metric = latest_metric
        self.enable_rolling_summary = False

        self.state = None
        self.header_shown = False
        self.pending_calls = {}
        self.thinking_task = None
        self.turn_start = None
        self.turn_tools = 0
        self.call_start_times = {}
        self.newline_buffer = ""
        self._last_char_newline = True  # New attribute

    async def render_stream(self, stream):
        self.turn_start = time.time()
        if not self.header_shown:
            self._render_header()
            self.header_shown = True

        try:
            async for event in stream:
                await self._render_event(event)
        except asyncio.CancelledError:
            self._print(f"\n{C.YELLOW}⚠{C.R} Interrupted by user.")
            if self.thinking_task:
                self.thinking_task.cancel()
        except Exception as e:
            from cogency.lib.logger import logger

            logger.error(f"Stream error: {e}")
            print(f"\n{C.RED}✗ Stream error: {e}{C.R}")
            raise

    def _render_header(self):
        parts = []

        # Get latest token count from metrics
        token_part = None
        if self.latest_metric and "total" in self.latest_metric:
            total = self.latest_metric["total"]
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
                    sep = f"{C.GRAY}---{C.R}\n" if self.state else ""
                    self._print(f"{sep}{C.CYAN}${C.R} {e['content']}")
                    self.state = "user"
                    self.thinking_task = asyncio.create_task(self._think_spin())

            case "intent":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    await asyncio.sleep(0)
                if e.get("content"):
                    self._print(f"{C.GRAY}intent: {e['content']}{C.R}")

            case "think":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    await asyncio.sleep(0)
                if e["content"] and e["content"].strip():
                    if self.state not in ("think", "result"):
                        self._print(f"{C.GRAY}~{C.R} ", end="", flush=True)
                        self.state = "think"
                        self.first_chunk = True
                    elif self.state == "result":
                        return
                    content = e["content"].lstrip() if self.first_chunk else e["content"]
                    if self.first_chunk:
                        self._print(f"{C.GRAY}{content}{C.R}", end="", flush=True)
                        self.first_chunk = False
                    else:
                        self._print(f"{C.GRAY}{content}{C.R}", end="", flush=True)

            case "respond":
                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    await asyncio.sleep(0)

                if not e["content"]:
                    return

                content = e["content"]

                # State transition: delay until we have real content
                if self.state != "respond":
                    if content.strip():
                        if not self._last_char_newline:
                            self._newline()
                        self._print(f"{C.MAGENTA}›{C.R} ", end="", flush=True)
                        self.state = "respond"
                        # Strip all leading whitespace including newlines from first token
                        self._print(render_markdown(content.strip()), end="", flush=True)
                    else:
                        self.newline_buffer += content
                    return

                # Already in respond state
                if content.strip():
                    # Real content - flush buffer then print
                    if self.newline_buffer:
                        self._print(render_markdown(self.newline_buffer), end="", flush=True)
                        self.newline_buffer = ""
                    self._print(render_markdown(content), end="", flush=True)
                else:
                    # Trailing whitespace - buffer it
                    self.newline_buffer += content

            case "call":
                from cogency.tools.parse import parse_tool_call

                if self.thinking_task:
                    self.thinking_task.cancel()
                    self.thinking_task = None
                    await asyncio.sleep(0)

                self.newline_buffer = ""
                self._newline()
                self.state = None
                self.turn_tools += 1

                try:
                    call = parse_tool_call(e.get("content", ""))
                    key = self._call_key(call)
                    self.pending_calls[key] = call
                    self.call_start_times[key] = time.time()
                    self._print(f"\r\033[K{C.GRAY}○ {format_call(call)}{C.R}", end="", flush=True)
                except Exception:
                    if self.pending_calls:
                        last_key = list(self.pending_calls.keys())[-1]
                        del self.pending_calls[last_key]

            case "result":
                call_key = None
                if self.pending_calls:
                    call_key = list(self.pending_calls.keys())[-1]
                    call = self.pending_calls.pop(call_key)
                    if start := self.call_start_times.pop(call_key, None):
                        time.time() - start

                    payload = e.get("payload", {})
                    is_error = payload.get("error", False)
                    symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
                    self._print(f"\r\033[K{symbol} {format_result(call, payload)}")

                    content = payload.get("content")
                    if content and call.name == "edit":
                        for line in render_diff(content):
                            self._print(line)

                    self.state = "result"
                    self.thinking_task = asyncio.create_task(self._think_spin())
                else:
                    payload = e.get("payload", {})
                    outcome = tool_outcome(payload)
                    if outcome:
                        message = outcome
                    else:
                        message = payload.get("message", "ok")
                    is_error = e.get("payload", {}).get("error")
                    symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
                    self._print(f"\r\033[K{symbol} {message}")
                    self.state = "result"
                    self.thinking_task = asyncio.create_task(self._think_spin())

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

    async def _spinner(self):
        if os.getenv("CI") == "true":
            return

        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                self._print(f"\r{C.GRAY}{frames[i]} loading ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.016)
        except asyncio.CancelledError:
            self._print("\r\033[K", end="", flush=True)

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
            self._print("\r\033[K", end="", flush=True)

    def _print(self, *args, **kwargs):
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
