import asyncio

from cogency.lib.color import C


async def _render_event(self, e):
    match e["type"]:
        case "user":
            if e["content"]:
                print(f"{C.gray}---{C.R}\n{C.cyan}${C.R} {e['content']}")
                self.state = "user"
                self.thinking_task = asyncio.create_task(self._think_spin())

        case "intent":
            if self.thinking_task:
                self.thinking_task.cancel()
                self.thinking_task = None
                print("\r\033[K", end="", flush=True)
            if e.get("content"):
                print(f"{C.gray}intent: {e['content']}{C.R}")

        case "think":
            if self.thinking_task:
                self.thinking_task.cancel()
                self.thinking_task = None
                print("\r\033[K", end="", flush=True)
            if e["content"] and e["content"].strip():
                if self.state != "think":
                    self._newline()
                    print(f"{C.gray}~{C.R} ", end="", flush=True)
                    self.state = "think"
                    self.first_chunk = True
                content = e["content"].lstrip() if self.first_chunk else e["content"]
                self.first_chunk = False
                print(content, end="", flush=True)

        case "respond":
            if self.thinking_task:
                self.thinking_task.cancel()
                self.thinking_task = None
                print("\r\033[K", end="", flush=True)
            if e["content"] and e["content"].strip():
                if self.state != "respond":
                    self._newline()
                    print(f"{C.magenta}>{C.R} ", end="", flush=True)
                    self.state = "respond"
                    self.first_chunk = True
                content = e["content"].lstrip() if self.first_chunk else e["content"]
                self.first_chunk = False
                print(content, end="", flush=True)

        case "call":
            from cogency.tools.parse import parse_tool_call

            if self.thinking_task:
                self.thinking_task.cancel()
                self.thinking_task = None
                print("\r\033[K", end="", flush=True)

            self._newline()
            self.state = None
            self.turn_tools += 1

            try:
                call = parse_tool_call(e.get("content", ""))
                key = self._call_key(call)
                self.pending_calls[key] = call
                self.result_buffers[key] = []
                print(f"{C.cyan}○{C.R} {self._fmt_call(call)}", end="", flush=True)
            except Exception:
                # Remove last call on exception
                if self.pending_calls:
                    last_key = list(self.pending_calls.keys())[-1]
                    del self.pending_calls[last_key]

        case "execute":
            if self.pending_calls:
                last_key = list(self.pending_calls.keys())[-1]
                self.spinner_task = asyncio.create_task(self._spin(self.pending_calls[last_key]))

        case "result":
            if self.spinner_task:
                self.spinner_task.cancel()
                self.spinner_task = None

            if self.pending_calls:
                last_key = list(self.pending_calls.keys())[-1]
                self.result_buffers.setdefault(last_key, []).append(e)
            else:
                outcome = self._fmt_result(None, e)
                is_error = e.get("payload", {}).get("error", False)
                symbol = f"{C.red}✗{C.R}" if is_error else f"{C.green}●{C.R}"
                print(f"\r\033[K{symbol} {outcome}\n", end="", flush=True)
            self.state = None

        case "end":
            if self.pending_calls:
                for key in list(self.pending_calls.keys()):
                    for buffered_event in self.result_buffers.get(key, []):
                        call = self.pending_calls.get(key)
                        outcome = self._fmt_result(call, buffered_event)
                        is_error = buffered_event.get("payload", {}).get("error", False)
                        symbol = f"{C.red}✗{C.R}" if is_error else f"{C.green}●{C.R}"
                        print(f"\r\033[K{symbol} {outcome}\n", end="", flush=True)
                    del self.pending_calls[key]
                    del self.result_buffers[key]
            self._newline()
            print()

        case "error":
            msg = e.get("payload", {}).get("error") or e.get("content", "Unknown error")
            print(f"{C.red}✗{C.R} {msg}")

        case "interrupt":
            print(f"{C.yellow}⚠{C.R} Interrupted")


def _call_key(self, call):
    # Return a hashable key for the call to distinguish concurrent calls
    return f"{call.name}::{str(call.args)}"
