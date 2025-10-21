"""Stream renderer - clean state machine for cogency events."""

import asyncio
import os
import re
import time

from .buffer import Buffer
from .color import C
from .diff import render_diff
from .format import format_call, format_result, tool_outcome
from .shell import format_shell_output
from .state import State


class Renderer:
    """Renders cogency event streams with explicit state transitions."""

    def __init__(self, verbose: bool = False, messages: list | None = None, config=None, **kwargs):
        self.verbose = verbose
        self.messages = messages or []
        self.config = config
        self.latest_metric = kwargs.get("latest_metric")

        self._state = State()
        self._buffer = Buffer()
        self._spinner_task = None
        self._turn_start = None

    async def render_stream(self, stream):
        """Main entry point - render all events from stream."""
        self._turn_start = time.time()
        self._render_header()

        try:
            async for event in stream:
                await self._dispatch(event)
        except asyncio.CancelledError:
            self._print(f"\n{C.YELLOW}⚠{C.R} Interrupted by user.")
            await self._cancel_spinner()
        except Exception as e:
            from cogency.lib.logger import logger

            logger.error(f"Stream error: {e}")
            raise
        finally:
            self._flush_buffer()

    async def _dispatch(self, event):
        """Dispatch event to appropriate handler."""
        etype = event["type"]

        if etype != "respond":
            self._flush_buffer()

        if etype == "user":
            await self._on_user(event)
        elif etype == "intent":
            await self._on_intent(event)
        elif etype == "think":
            await self._on_think(event)
        elif etype == "respond":
            await self._on_respond(event)
        elif etype == "call":
            await self._on_call(event)
        elif etype == "result":
            await self._on_result(event)
        elif etype == "end":
            await self._on_end()
        elif etype == "error":
            self._on_error(event)
        elif etype == "interrupt":
            self._on_interrupt()
        elif etype == "metric":
            self.latest_metric = event

    async def _on_user(self, e):
        self._state = self._state.reset_turn()
        if not e.get("content"):
            return
        sep = f"{C.GRAY}---{C.R}\n" if self._state.phase != "idle" else ""
        self._print(f"{sep}{C.CYAN}${C.R} {e['content']}")
        self._state = self._state.with_phase("user")
        self._spinner_task = asyncio.create_task(self._spin("thinking"))

    async def _on_intent(self, e):
        await self._cancel_spinner()
        if e.get("content"):
            self._print(f"{C.GRAY}intent: {e['content']}{C.R}")

    async def _on_think(self, e):
        await self._cancel_spinner()
        content = e.get("content", "")
        if not content:
            return

        if self._state.phase != "think":
            if self._state.phase in ("result", "respond") and not self._state.last_char_newline:
                self._newline()
            self._print(f"{C.GRAY}~{C.R} ", end="", flush=True)
            self._state = self._state.with_phase("think")
            content = content.lstrip()

        self._print(f"{C.GRAY}{content}{C.R}", end="", flush=True)
        self._state = self._state.with_newline_flag(content.endswith("\n"))

    async def _on_respond(self, e):
        await self._cancel_spinner()
        if not e["content"].strip():
            return

        content = e["content"]
        if not self._state.response_started:
            if self._state.phase == "think" and not self._state.last_char_newline:
                self._newline(force=True)
            elif not self._state.last_char_newline:
                self._newline()
            self._print(f"{C.MAGENTA}›{C.R} ", end="", flush=True)
            self._state = self._state.with_phase("respond").with_response_started(True)
            content = content.lstrip("\n")

        self._buffer.append(content)
        last_newline = self._buffer.flush_incremental(
            lambda txt, **kw: self._print(txt, **kw), delimiter="\n\n", buffer_leading_ws=True
        )
        self._state = self._state.with_newline_flag(last_newline)

    async def _on_call(self, e):
        from cogency.core.codec import parse_tool_call

        self._state = self._state.reset_turn()
        await self._cancel_spinner()

        self._newline()
        self._state = self._state.with_phase("call")

        try:
            call = parse_tool_call(e.get("content", ""))
            key = self._call_key(call)
            self._state = self._state.add_call(key, call)
            self._print(f"\r\033[K{C.GRAY}○ {format_call(call)}{C.R}", end="", flush=True)
            self._state = self._state.with_newline_flag(False)
        except Exception:
            self._state, popped = self._state.pop_call()

    async def _on_result(self, e):
        self._state, popped = self._state.pop_call()

        if popped:
            key, call = popped
            payload = e.get("payload", {})
            is_error = payload.get("error", False)
            symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
            self._print(f"\r\033[K{symbol} {format_result(call, payload)}")
            self._state = self._state.with_newline_flag(True)

            content = payload.get("content")
            if content and call.name == "edit":
                for line in render_diff(content):
                    self._print(line)
            elif content and call.name == "shell":
                exit_code = 0
                outcome = payload.get("outcome", "")
                if m := re.search(r"exit (\d+)", outcome):
                    exit_code = int(m.group(1))
                formatted = format_shell_output(content, exit_code)
                for line in formatted.split("\n"):
                    self._print(line)
        else:
            payload = e.get("payload", {})
            outcome = tool_outcome(payload)
            message = outcome if outcome else payload.get("message", "ok")
            is_error = payload.get("error")
            symbol = f"{C.RED}✗{C.R}" if is_error else f"{C.GREEN}●{C.R}"
            self._print(f"\r\033[K{symbol} {message}")
            self._state = self._state.with_newline_flag(True)

        self._state = self._state.with_phase("result")
        self._spinner_task = asyncio.create_task(self._spin("thinking"))

    async def _on_end(self):
        self._state = self._state.reset_turn().clear_calls()
        self._newline()

    def _on_error(self, e):
        msg = e.get("payload", {}).get("error") or e.get("content", "Unknown error")
        self._print(f"{C.RED}✗{C.R} {msg}")

    def _on_interrupt(self):
        self._print(f"{C.YELLOW}⚠{C.R} Interrupted")

    def _render_header(self):
        """Render session header with stats."""
        total_tokens = 0
        if self.latest_metric and "total" in self.latest_metric:
            total = self.latest_metric["total"]
            total_tokens = total.get("input", 0) + total.get("output", 0)

        token_part = f"{total_tokens / 1000:.1f}k tokens"
        msg_count = len(self.messages) if self.messages else 0
        msg_part = f"{msg_count} msgs"
        tools_count = sum(1 for m in self.messages if m.get("type") == "call")
        tool_part = f"{tools_count} tools"

        model_name = "unknown"
        if self.config and hasattr(self.config, "model") and self.config.model:
            model_name = self.config.model
        elif self.config and hasattr(self.config, "provider") and self.config.provider:
            model_name = self.config.provider

        parts = [token_part, msg_part, tool_part, model_name]
        self._print(f"{C.GRAY}{' · '.join(parts)}{C.R}")

    async def _spin(self, label: str):
        """Show spinner while waiting."""
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

    async def _cancel_spinner(self):
        if self._spinner_task:
            self._spinner_task.cancel()
            self._spinner_task = None
            await asyncio.sleep(0)

    def _print(self, *args, **kwargs):
        """Print and track newline state."""
        actual_end = kwargs.get("end", "\n")
        print(*args, **kwargs)
        self._state = self._state.with_newline_flag(actual_end == "\n")

    def _newline(self, force: bool = False):
        """Add newline if needed."""
        if (
            force or self._state.phase not in ("respond", "think")
        ) and not self._state.last_char_newline:
            self._print()

    def _flush_buffer(self):
        """Flush respond buffer to output."""
        if not self._buffer.empty:
            last_newline = self._buffer.flush_to(lambda txt, **kw: self._print(txt, **kw))
            self._state = self._state.with_newline_flag(last_newline)

    def _call_key(self, call):
        """Generate unique key for call tracking."""
        return f"{call.name}::{str(call.args)}"
