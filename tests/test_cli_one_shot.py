"""Tests for CLI one-shot behavior."""

import sys
from types import SimpleNamespace


def test_cli_one_shot_uses_direct_instructions(monkeypatch, tmp_path):
    """CLI invocation should instruct agent to answer immediately without greeting."""
    captured = {}
    emitted_events = []

    class FakeAgent:
        def __init__(self, *_, **kwargs):
            captured["instructions"] = kwargs.get("instructions")
            captured["identity"] = kwargs.get("identity")
            self.config = SimpleNamespace(llm=None)

        def __call__(self, *_, **__):
            async def stream():
                yield {"type": "respond", "content": "4"}
                yield {"type": "end", "content": ""}

            return stream()

    class FakeRenderer:
        async def render_stream(self, stream):
            async for event in stream:
                emitted_events.append(event)

    monkeypatch.setenv("COGENCY_CODE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr("cogency.core.agent.Agent", FakeAgent)
    monkeypatch.setattr("cogency.cli.display.Renderer", lambda: FakeRenderer())

    dummy_clipboard = SimpleNamespace(copy=lambda *_: None, paste=lambda: "")
    monkeypatch.setitem(sys.modules, "pyperclip", dummy_clipboard)

    from cogency_code.__main__ import main

    original_argv = sys.argv[:]
    try:
        sys.argv = ["cogency-code", "what", "is", "2+2"]
        main()
    finally:
        sys.argv = original_argv
        monkeypatch.delenv("COGENCY_CODE_CONFIG_DIR", raising=False)

    assert captured["instructions"] is not None
    assert "CLI ONE-SHOT MODE" in captured["instructions"]
    assert "Do not introduce yourself" in captured["instructions"]
    assert emitted_events and emitted_events[0]["content"] == "4"
