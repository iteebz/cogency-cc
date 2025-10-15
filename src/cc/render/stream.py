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
from .shell import format_shell_output


def render_markdown(text: str) -> str:
    """Render markdown with ANSI codes."""
    # No special handling needed for line breaks - they should be preserved naturally

    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", f"{C.BOLD}\\1{C.R}", text)

    # Italic: *text* (but not list markers)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)", "\033[3m\\1\033[0m", text)

    # Inline code: `code`
    text = re.sub(r"`([^`]+)`", f"{C.GRAY}\\1{C.R}", text)

    # Headers: # text
    text = re.sub(r"^(#{1,6})\s+(.+)$", f"{C.BOLD}{C.CYAN}# \\2{C.R}", text, flags=re.MULTILINE)

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
        self.response_started_this_turn = False
        self.respond_buffer = ""  # Added this line
        self._last_char_newline = True  # New attribute

    async def render_stream(self, stream):
        self.turn_start = time.time()
        self._render_header()

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
            raise
        finally:
            self._flush_respond_buffer()

    def _render_header(self):
        parts = []

        total_tokens = 0
        if self.latest_metric and "total" in self.latest_metric:
            total = self.latest_metric["total"]
            total_tokens = total.get("input", 0) + total.get("output", 0)

        token_part = f"{total_tokens / 1000:.1f}k tokens"  # Always display, even if 0

        msg_count = len(self.messages) if self.messages else 0
        msg_part = f"{msg_count} msgs"

        tools_count = sum(1 for m in self.messages if m.get("type") == "call")
        tool_part = f"{tools_count} tools"

        model_name = "unknown"
        if self.config and hasattr(self.config, "model") and self.config.model:
            model_name = self.config.model
        elif self.config and hasattr(self.config, "provider") and self.config.provider:
            model_name = self.config.provider

        parts = []
        parts.append(token_part)  # Always append token_part
        parts.append(msg_part)
        parts.append(tool_part)
        parts.append(model_name)

        if parts:
            self._print(f"{C.GRAY}{' · '.join(parts)}{C.R}")

    async def _render_event(self, e):
        if e["type"] != "respond":
            self._flush_respond_buffer()

        match e["type"]:
            case "user":
                await self._handle_user(e)
            case "intent":
                await self._handle_intent(e)
            case "think":
                await self._handle_think(e)
            case "respond":
                await self._handle_respond(e)
            case "call":
                await self._handle_call(e)
            case "result":
                await self._handle_result(e)
            case "end":
                await self._handle_end()
            case "error":
                self._handle_error(e)
            case "interrupt":
                self._handle_interrupt()
            case "metric":
                self.latest_metric = e

    def _reset_turn(self):
        self.response_started_this_turn = False

    def _start_result_spinner(self):
        self.state = "result"
        self.thinking_task = asyncio.create_task(self._think_spin())

    async def _handle_user(self, e):
        self._reset_turn()
        if e["content"]:
            sep = f"{C.GRAY}---{C.R}\n" if self.state else ""
            self._print(f"{sep}{C.CYAN}${C.R} {e['content']}")
            self.state = "user"
            self.thinking_task = asyncio.create_task(self._think_spin())

    async def _handle_intent(self, e):
        await self._cancel_spinner()
        if e.get("content"):
            self._print(f"{C.GRAY}intent: {e['content']}{C.R}")

    async def _handle_think(self, e):
        await self._cancel_spinner()

        content = e.get("content", "")
        if not content:
            return

        if self.state != "think":
            if self.state == "result" and not self._last_char_newline:
                self._newline()
            self._print(f"{C.GRAY}~{C.R} ", end="", flush=True)
            self.state = "think"
            self.first_chunk = True

        # Only strip leading whitespace for the first chunk to maintain spaces between words
        if self.first_chunk:
            content_to_print = content.lstrip()
            self.first_chunk = False
        else:
            content_to_print = content

        self._print(f"{C.GRAY}{content_to_print}{C.R}", end="", flush=True)

    async def _handle_respond(self, e):
        await self._cancel_spinner()

        if not e["content"].strip():
            return

        if not self.response_started_this_turn:
            if self.state == "think" and not self._last_char_newline:
                self._newline(force=True)
            elif not self._last_char_newline:
                self._newline()
            self._print(f"{C.MAGENTA}›{C.R} ", end="", flush=True)
            self.state = "respond"
            self.response_started_this_turn = True

        self.respond_buffer += e["content"]

    async def _handle_call(self, e):
        from cogency.core.codec import parse_tool_call

        self._reset_turn()
        await self._cancel_spinner()

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

    async def _handle_result(self, e):
        if self.pending_calls:
            call_key = list(self.pending_calls.keys())[-1]
            call = self.pending_calls.pop(call_key)
            self.call_start_times.pop(call_key, None)

            payload = e.get("payload", {})
            is_error = payload.get("error", False)
            symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
            self._print(f"\r\033[K{symbol} {format_result(call, payload)}")

            content = payload.get("content")
            if content and call.name == "edit":
                for line in render_diff(content):
                    self._print(line)
            elif content and call.name == "shell":
                exit_code = 0
                outcome = payload.get("outcome", "")
                if m := re.search(r"exit (\d+)", outcome):
                    exit_code = int(m.group(1))
                formatted_output = format_shell_output(content, exit_code)
                for line in formatted_output.split("\n"):
                    self._print(line)

            self._start_result_spinner()
        else:
            payload = e.get("payload", {})
            outcome = tool_outcome(payload)
            message = outcome if outcome else payload.get("message", "ok")
            is_error = payload.get("error")
            symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
            self._print(f"\r\033[K{symbol} {message}")
            self._start_result_spinner()

    async def _handle_end(self):
        self._reset_turn()
        if self.pending_calls:
            for key in list(self.pending_calls.keys()):
                self.call_start_times.pop(key, None)
            self.pending_calls.clear()
        self._newline()
        await self._finalize()

    def _handle_error(self, e):
        msg = e.get("payload", {}).get("error") or e.get("content", "Unknown error")
        self._print(f"{C.RED}✗{C.R} {msg}")

    def _handle_interrupt(self):
        self._print(f"{C.YELLOW}⚠{C.R} Interrupted")

    async def _spin(self, label: str):
        if os.getenv("CI") == "true":
            return

        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        start = time.time()
        try:
            while True:
                elapsed = int(time.time() - start)
                self._print(f"\r{C.GRAY}{frames[i]} {label} ({elapsed}s){C.R}", end="", flush=True)
                i = (i + 1) % len(frames)
                await asyncio.sleep(0.016)
        except asyncio.CancelledError:
            self._print("\r\033[K", end="", flush=True)

    async def _think_spin(self):
        await self._spin("thinking")

    async def _cancel_spinner(self):
        if self.thinking_task:
            self.thinking_task.cancel()
            self.thinking_task = None
            await asyncio.sleep(0)

    def _print(self, *args, **kwargs):
        actual_end = kwargs.get("end", "\n")
        print(*args, **kwargs)
        self._last_char_newline = actual_end == "\n"

    def _newline(self, force: bool = False):
        # Only add newline if not transitioning to respond state or if there's buffered content
        if (
            force or self.state not in ("respond", "think") or self.newline_buffer
        ) and not self._last_char_newline:
            self._print()

    def _call_key(self, call):
        # Return a hashable key for the call to distinguish concurrent calls
        return f"{call.name}::{str(call.args)}"

    def _flush_respond_buffer(self):
        if self.respond_buffer:
            # Only trim leading newlines, preserve trailing newlines
            trimmed_content = self.respond_buffer.lstrip("\n")
            # Only apply markdown rendering if content contains markdown patterns
            if is_markdown_content(trimmed_content):
                # Print content with markdown rendering
                self._print(render_markdown(trimmed_content), end="")
            else:
                # Print content as-is, letting print() handle line breaks naturally
                self._print(trimmed_content, end="")
            self.respond_buffer = ""

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
        from cogency.lib.storage import SummaryStorage

        from ..storage import storage as get_storage

        msg_storage = get_storage(self.config)
        sum_storage = SummaryStorage()
        threshold = getattr(self.config, "compact_threshold", 10)

        culled = await maybe_cull(
            self.conv_id, "cogency", msg_storage, sum_storage, self.llm, threshold
        )

        if culled:
            new_id = str(uuid.uuid4())
            self.config.update(conversation_id=new_id)
            logger.debug(f"🔄 EVO: compacted → new conv {new_id[:8]}")
