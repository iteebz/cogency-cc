"""Minimal stream renderer - just print events."""

import json

GRAY = "\033[90m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
R = "\033[0m"


async def render(stream):
    try:
        async for event in stream:
            match event["type"]:
                case "user":
                    if event.get("content"):
                        print(f"{CYAN}${R} {event['content']}")
                case "think":
                    if event.get("content"):
                        print(f"{GRAY}{event['content']}{R}", end="", flush=True)
                case "respond":
                    if event.get("content"):
                        print(event["content"], end="", flush=True)
                case "call":
                    call = json.loads(event.get("content", "{}"))
                    name = call.get("name", "?")
                    args = call.get("args", {})
                    arg_str = ", ".join(f"{k}={v!r}" for k, v in list(args.items())[:2])
                    if len(args) > 2:
                        arg_str += ", ..."
                    print(f"\n{GRAY}○ {name}({arg_str}){R}")
                case "result":
                    payload = event.get("payload", {})
                    is_error = payload.get("error", False)
                    symbol = f"{RED}✗{R}" if is_error else f"{GREEN}●{R}"
                    msg = payload.get("outcome") or payload.get("message") or "ok"
                    print(f"{symbol} {msg}")
                case "error":
                    msg = event.get("payload", {}).get("error") or event.get("content", "error")
                    print(f"{RED}✗ {msg}{R}")
                case "end":
                    print()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}interrupted{R}")


class Renderer:
    def __init__(self, **kwargs):
        pass

    async def render_stream(self, stream):
        await render(stream)
