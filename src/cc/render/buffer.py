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

    def flush_incremental(
        self, printer, delimiter: str | None = None, buffer_leading_ws: bool = False
    ) -> bool:
        """Flush accumulated content up to delimiter, optionally buffering leading whitespace."""
        if self._flushed_len >= len(self._content):
            return self._last_char_newline

        chunk = self._content[self._flushed_len :]
        delim_pos = -1

        to_flush = chunk
        if delimiter:
            delim_pos = chunk.find(delimiter)
            if delim_pos >= 0:
                to_flush = chunk[:delim_pos]
                self._flushed_len += delim_pos + len(delimiter)

                if buffer_leading_ws:
                    remaining = self._content[self._flushed_len :]
                    ws_count = len(remaining) - len(remaining.lstrip())
                    self._flushed_len += ws_count
            else:
                nl_pos = chunk.find("\n")
                if nl_pos >= 0:
                    to_flush = chunk[: nl_pos + 1]
                    self._flushed_len += nl_pos + 1
                else:
                    self._flushed_len = len(self._content)
        else:
            self._flushed_len = len(self._content)

        if buffer_leading_ws and delimiter:
            to_flush_stripped = to_flush.rstrip() if delim_pos >= 0 else to_flush

            if not to_flush_stripped.strip():
                self._last_char_newline = True
                return True

            to_flush_stripped = to_flush_stripped.lstrip("\n")
        else:
            if delimiter and delim_pos < 0:
                to_flush_stripped = to_flush
            else:
                to_flush_stripped = to_flush.rstrip() if delimiter else to_flush

        if not to_flush_stripped.strip():
            self._last_char_newline = (
                self._content.endswith("\n") if delimiter else to_flush.endswith("\n")
            )
            return self._last_char_newline

        if is_markdown(to_flush_stripped):
            self._has_markdown = True

        if self._has_markdown:
            to_flush_stripped = render_markdown(to_flush_stripped)

        printer(to_flush_stripped, end="")

        if delimiter and delim_pos >= 0:
            printer(delimiter, end="")
            self._last_char_newline = True
        else:
            self._last_char_newline = to_flush_stripped.endswith("\n")

        return self._last_char_newline

    def flush_to(self, printer) -> bool:
        """Flush remaining buffer to printer function. Returns whether newline ended output."""
        if self._flushed_len >= len(self._content):
            return self._last_char_newline

        chunk = self._content[self._flushed_len :]
        trimmed = chunk.lstrip("\n")
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
