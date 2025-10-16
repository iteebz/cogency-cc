"""Output buffer - handles buffering and flushing logic."""

from .format import is_markdown, render_markdown


class Buffer:
    """Manages buffered output and flushes to print."""

    def __init__(self):
        self._content = ""
        self._last_char_newline = True

    def append(self, text: str):
        """Add text to buffer."""
        self._content += text

    def flush_to(self, printer) -> bool:
        """Flush buffer to printer function. Returns whether newline ended output."""
        if not self._content:
            return self._last_char_newline

        trimmed = self._content.lstrip("\n")
        if not trimmed:
            self._content = ""
            return self._last_char_newline

        if is_markdown(trimmed):
            printer(render_markdown(trimmed), end="")
        else:
            printer(trimmed, end="")

        self._last_char_newline = trimmed.endswith("\n")
        self._content = ""
        return self._last_char_newline

    def clear(self):
        """Clear buffer without flushing."""
        self._content = ""

    @property
    def empty(self) -> bool:
        return not self._content

    @property
    def last_char_newline(self) -> bool:
        return self._last_char_newline

    def set_newline_flag(self, flag: bool):
        self._last_char_newline = flag
