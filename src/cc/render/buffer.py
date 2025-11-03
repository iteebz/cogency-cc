"""Output buffer - handles buffering and flushing logic."""

from .format import is_markdown, render_markdown


def _find_boundary(chunk: str, delimiter: str | None) -> tuple[str, int, bool]:
    """Find boundary (delimiter or newline) in chunk.

    Returns:
        (text_to_flush, chars_to_skip, found_delimiter)
    """
    if delimiter:
        delim_pos = chunk.find(delimiter)
        if delim_pos >= 0:
            return chunk[:delim_pos], delim_pos + len(delimiter), True

    nl_pos = chunk.find("\n")
    if nl_pos >= 0:
        return chunk[: nl_pos + 1], nl_pos + 1, False

    return chunk, len(chunk), False


def _trim_for_output(
    text: str, found_delim: bool, has_delim_arg: bool, buffer_leading_ws: bool
) -> str:
    """Normalize text for output based on boundary type and options."""
    if buffer_leading_ws and has_delim_arg:
        text = text.rstrip() if found_delim else text
        text = text.lstrip("\n")
    else:
        if has_delim_arg and not found_delim:
            text = text
        else:
            text = text.rstrip() if has_delim_arg else text

    return text


class Buffer:
    """Manages buffered output with incremental flushing."""

    def __init__(self):
        self._content = ""
        self._last_char_newline = True
        self._has_markdown = False
        self._flushed_len = 0

    def append(self, text: str):
        """Add text to buffer and track markdown presence."""
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
        to_flush, skip_chars, found_delim = _find_boundary(chunk, delimiter)
        self._flushed_len += skip_chars

        if buffer_leading_ws and delimiter and found_delim:
            remaining = self._content[self._flushed_len :]
            ws_count = len(remaining) - len(remaining.lstrip())
            self._flushed_len += ws_count

        to_flush_stripped = _trim_for_output(
            to_flush, found_delim, bool(delimiter), buffer_leading_ws
        )

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

        if delimiter and found_delim:
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
