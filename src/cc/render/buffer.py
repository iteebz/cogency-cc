"""Output buffer - handles buffering and flushing logic."""

from .format import is_markdown, render_markdown


class Buffer:
    """Manages buffered output with incremental flushing."""

    def __init__(self):
        self._content = ""
        self._last_char_newline = True
        self._has_markdown = False
        self._flushed_len = 0

    def append(self, text: str):
        """Add text to buffer and flush incrementally."""
        self._content += text
        if is_markdown(text):
            self._has_markdown = True

    def flush_incremental(self, printer) -> bool:
        """Flush accumulated content since last flush. Returns whether newline ended output."""
        if self._flushed_len >= len(self._content):
            return self._last_char_newline

        chunk = self._content[self._flushed_len:]
        if not chunk.strip():
            self._flushed_len = len(self._content)
            self._last_char_newline = self._content.endswith("\n")
            return self._last_char_newline

        if is_markdown(chunk):
            self._has_markdown = True
        
        if self._has_markdown:
            chunk = render_markdown(chunk)
        
        printer(chunk, end="")
        self._flushed_len = len(self._content)
        self._last_char_newline = self._content.endswith("\n")
        return self._last_char_newline

    def flush_to(self, printer) -> bool:
        """Flush remaining buffer to printer function. Returns whether newline ended output."""
        if not self._content:
            return self._last_char_newline

        trimmed = self._content.lstrip("\n")
        if not trimmed:
            self._content = ""
            self._flushed_len = 0
            return self._last_char_newline

        if is_markdown(trimmed):
            printer(render_markdown(trimmed), end="")
        else:
            printer(trimmed, end="")

        self._last_char_newline = trimmed.endswith("\n")
        self._content = ""
        self._flushed_len = 0
        return self._last_char_newline

    def clear(self):
        """Clear buffer without flushing."""
        self._content = ""
        self._flushed_len = 0
        self._has_markdown = False

    @property
    def empty(self) -> bool:
        return not self._content

    @property
    def last_char_newline(self) -> bool:
        return self._last_char_newline

    def set_newline_flag(self, flag: bool):
        self._last_char_newline = flag
