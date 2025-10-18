# Terminal Rendering Protocol

cogency-cc renders cogency events as terminal output. Events are contracts; no protocol negotiation.

## Event Types

| Event | Persisted | Behavior |
|-------|-----------|----------|
| `user` | ✓ | Print query with cyan `$`, start spinner |
| `think` | ✓ | Print reasoning with gray `~` |
| `call` | ✓ | Print formatted tool invocation |
| `result` | ✓ | Print outcome (green `✓` / red `✗`) + content |
| `respond` | ✓ | Accumulate in buffer, stream at newlines |
| `end` | ✗ | Close response, print metrics |
| `error` | ✗ | Print error message |
| `interrupt` | ✗ | Print interruption warning |
| `metric` | ✗ | Token counts + timing (printed with `end`) |

## Phase State Machine

```
IDLE
  ↓ user
USER (print query, spinner)
  ↓ think
THINK (print reasoning)
  ↓ call
CALL (print tool)
  ↓ result
RESULT (print outcome)
  ↓ respond
RESPOND (stream response)
  ↓ end
IDLE (print metrics)
```

## Dispatch Rules

```python
async def _dispatch(self, event):
    # Flush buffer before non-respond phase changes
    if event["type"] != "respond":
        self._flush_buffer()
    
    # Handle event
    if event["type"] == "user":
        self._state = self._state.with_phase("user")
        print(f"$ {event['content']}")
        start_spinner()
    
    elif event["type"] == "respond":
        # Accumulate (don't flush yet)
        self._buffer.append(event["content"])
        self._buffer.flush_incremental(print, delimiter="\n")
```

**Key insight:** Non-respond events interrupt buffer. Respond events stream at newline boundaries.

## Formatting

**Prefixes:**
- `$` cyan — User query
- `~` gray — Thinking
- `✓` green — Success
- `✗` red — Error
- `───` gray — Turn separator

**Example:**
```
$ What's in main.py?
~ I need to read the file

read("main.py")
✓ Found 50 lines
<file content>

The file contains a Flask app with routes.
───
Input: 120  Output: 80  Duration: 1.2s
```

## Buffer Flushing

```python
class Buffer:
    _content: str          # Text accumulating
    _flushed_len: int      # Position of last flush
    _last_char_newline: bool
    _has_markdown: bool    # Contains markdown?

# Append text
buffer.append("Some response...")

# Flush at newline (markdown detection happens here)
buffer.flush_incremental(printer, delimiter="\n")
```

**Rules:**
1. Detect markdown on append
2. Render markdown on flush (need full block)
3. Flush at newline or delimiter
4. Track newline state (no double-newlines)
5. Strip trailing whitespace

**Why?** Streaming character-by-character. Buffer until semantic boundary. Detect markdown before printing.

## Newline Tracking

State tracks `last_char_newline: bool`:

```python
# Before printing
if state.last_char_newline and phase != "idle":
    print("───\n")  # Separator before new turn

# After printing
state = state.with_newline_flag(output.endswith("\n"))
```

Prevents double-newlines and orphaned formatting.

## History Rendering

On session start, load previous messages:

```python
messages = await storage.load_messages(conv_id, user_id)
renderer = Renderer(messages=messages)
```

History reconstructed as events and rendered in gray to distinguish from live interaction.

## Error Handling

On exception:
```python
except Exception as e:
    logger.error(f"Stream error: {e}")
    print(f"\n{RED}Error: {e}{RESET}")
    exit(1)
```

On user interrupt (Ctrl+C):
```python
except asyncio.CancelledError:
    print(f"\n{YELLOW}⚠{RESET} Interrupted by user.")
    # Cancel spinner, flush buffer, clean exit
```

## Full Example

**Input stream:**
```json
{"type": "user", "content": "What's in main.py?"}
{"type": "think", "content": "I should read the file"}
{"type": "call", "content": "{\"name\": \"read\", \"args\": {\"file\": \"main.py\"}}"}
{"type": "result", "payload": {"outcome": "Read 50 lines", "content": "def main(): ..."}}
{"type": "respond", "content": "The file contains a main function."}
{"type": "end"}
{"type": "metric", "step": {"input": 60, "output": 40}, "total": {"input": 120, "output": 80}}
```

**Output:**
```
$ What's in main.py?
~ I should read the file

read("main.py")
✓ Read 50 lines
def main(): ...

The file contains a main function.
───
Input: 120  Output: 80
```

Events fire dispatch → state transition → buffer operation → print. All state immutable (snapshots only).
