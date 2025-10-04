# Cogency-Code Context

## Architecture Decisions

### Mode="replay" is Essential
- **DO NOT REMOVE** `mode="replay"` from agent.py line 25
- This is the essential fallback mechanism for reliable operation
- The agent must default to replay mode for predictable behavior
- This is non-negotiable for stability

### User Identity Pattern
- `user_id="cogency"` (consistent across main entry point)
- `identity="coding"` (fixed for this application)
- Do not change these values - they are core to the system

### Protocol Format
- Current issue: Mock LLM returns `§execute` but cogency expects `§call:`
- Need to align protocol formats between mock and actual system

### Debug Infrastructure Status
- Current test setup has debug prints (conftest.py lines 26-29)
- These should remain for debugging integration issues
- MockLLM is designed to expose message passing problems

## Core Problem Being Solved

The agent fails because user queries don't reach the LLM. The integration layer between cogency-code and cogency core loses user content during message assembly.

## Current Test Strategy

1. MockLLM captures and prints all received messages
2. Tests verify that user content actually reaches the LLM
3. Tool execution is secondary to message passing verification
4. Debug prints are intentional for integration debugging

## Files Modified

- `src/cogency_code/__main__.py` - Fixed identity from "cogency" to "coding"
- `src/cogency_code/agent.py` - Added mode="replay" for stability
- `tests/conftest.py` - MockLLM for testing without API keys
- `tests/test_agent_tools.py` - Integration test to reproduce query passing failure

## Non-Negotiable Requirements

- `mode="replay"` stays in agent.py
- Debug infrastructure remains for integration debugging
- User identity pattern stays consistent
- Focus on fixing message assembly, not removing safeguards