# Example 01: Customer support refund agent (LangGraph)

This directory demonstrates Phase 0 behavioral tests for a mock refund workflow: LangGraph `ToolNode` execution with `HarnessInterceptor` in **mock** mode (AD-005), YAML `steps` that drive scripted tool calls, and Agent-Harness assertions on the resulting trace.

## Prerequisites

```bash
pip install -e ".[langgraph,dev]"
```

## Run tests

From the repository root:

```bash
python -m pytest examples/01_customer_support_langgraph/
```

## Layout

- `support/refund_tools.py` — LangChain tools (lookup, eligibility, refund, approval, escalation).
- `support/executor.py` — loads scenario YAML with a `steps` list, runs tools via `create_intercepted_tool_node`, builds a trace with `input.value` args.
- `scenarios/*.yaml` — five scenarios (happy path, limit guard, ineligible order, loop guard, mutual exclusion).
- `test_refund_agent.py` — one pytest per scenario using `@scenario` and the local `run` fixture (overrides the default `run` from the Agent-Harness pytest plugin for this package).
