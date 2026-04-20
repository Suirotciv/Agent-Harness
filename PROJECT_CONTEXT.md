# project_context.md
## AgentHarness -- Project Intelligence & Working Context
### Living Document -- Last Updated: April 2026 (Phase 0 exit review complete)

> **How to use this file:**
> This is the single source of truth for anyone working on AgentHarness. It is the first file you read before touching code and the last file you update before closing a PR. It does not replace the full proposal (project_proposal.md) or the roadmap -- it is the working layer on top of them. When you discover something important -- an architectural decision, a constraint, a lesson, a changed assumption -- you write it here. This file should make any engineer productive in 30 minutes regardless of how long they've been away from the project.

---

## Document change policy

`project_context.md` is **append-first**: we do not erase authoritative history.

1. Use ~~strikethrough~~ (`~~...~~`) only when **existing text is no longer correct** and you are preserving what it replaced. If you only add a clarification or extend a still-valid sentence, edit in place — do not duplicate unchanged wording. Strike the obsolete fragment or sentence, then show the current text. In the raw editor, tildes stay visible; on GitHub and in Markdown Preview, struck text renders crossed out.
2. When a change is **too large** for readable inline strike-through (multi-paragraph sections, whole table snapshots), add a dated entry to [project_context_revisions.md](project_context_revisions.md) with the **full prior text** and a short note on what replaced it.
3. Every substantive edit to this file should add a **newest-first** entry to `project_context_revisions.md`.

---

## CURRENT STATUS

```
Phase:        1 -- MVP
Checkpoint:   1 of 3
Blockers:     None
Last Updated: April 2026
```

### What We Are Building Right Now
~~The tool intercept layer and basic trace schema. Everything else depends on getting this right. If tool calls cannot be reliably intercepted and recorded -- for both sync and async callables -- without modifying the agent's source code, the rest of the project does not work.~~

The tool intercept layer and basic trace schema. The first slice of interception is implemented and tested for LangGraph (native `ToolNode` hooks plus AD-002 fallback; sync and async; mock and live). ~~Next: formal `Span` / `Trace` models,~~ `Span` / `Trace` Pydantic models and OpenInference-aligned attribute keys are in `core/trace.py` and `telemetry/schema.py`. `assert_called_before` is implemented in `assertions/structural.py` (see Sprint 1 table). Trace JSONL serialization is in `telemetry/jsonl.py` (AD-008; import from `agentharness.telemetry.jsonl`). **Assertions API:** every public harness assertion returns an `AssertionResult` (`assertions/base.py`) with `regulatory_refs` (mapped via `REFS_*` constants to EU AI Act, NIST AI RMF TEVV, Colorado SB 24-205, OWASP LLM citations) and a `details` dict for reporters; `finish()` raises `AssertionError` on failure so pytest behavior is unchanged (AD-011). ~~Next: telemetry collector wiring from `ToolCallRecord` into spans.~~ Phase 1 Checkpoint 1 underway. ~~Priority: `telemetry/collector.py` (ToolCallRecord → Span),~~ `TraceCollector` is implemented (`telemetry/collector.py`; import from `agentharness.telemetry.collector`). Next priorities: cassette record/replay pipeline, regression diff, and 0.1.0-alpha PyPI release.

### This Week's Priority
1. ~~Validate that LangGraph's `ToolNode` can be wrapped without patching LangGraph internals (sync and async)~~ **Done** -- see `tests/unit/test_langgraph_intercept.py` and DOMAIN KNOWLEDGE / LangGraph discovery below.
2. ~~Define the Span schema (see Architecture Decisions below)~~ **Done** -- `core/trace.py`, `telemetry/schema.py`; ~~next: implement `telemetry/collector.py` and connect `ToolCallRecord` → `Span`.~~ **Done** — `telemetry/collector.py` (`TraceCollector`).
3. **Done** — `assert_called_before` plus `tests/unit/test_assert_called_before.py` (trace spans, interceptor `ToolCallRecord` list, ordered name lists).

---

## WHAT WE ARE BUILDING

### One-Sentence Description
AgentHarness is an open-source test harness for AI agents that take real-world actions -- it lets engineering teams write behavioral tests for agents, run those tests in CI, and generate compliance evidence, all without calling real APIs.

### The Core Problem It Solves
Engineering teams can observe what their agent did (via tracing tools like LangFuse and Arize Phoenix) and score what their agent said (via evaluation tools like LangSmith and DeepEval). No single open-source, framework-agnostic tool lets them assert that their agent *did the right things in the right order* -- with deterministic record/replay, fault injection, regression diffing, and compliance evidence generation -- as an automated CI test. We build that tool.

### What It Is Not
- Not a monitoring or observability platform (use LangFuse or Arize Phoenix for that)
- Not a full LLMOps platform
- Not framework-specific (not a LangChain product)
- Not an LLM benchmark (not SWE-bench or WebArena)
- Not a replacement for LangSmith, DeepEval, or TruLens -- it is complementary, focusing on the behavioral testing layer they do not fully cover

---

## ARCHITECTURE DECISIONS

> All major decisions are logged here with reasoning. Never change these without updating this entry. If you disagree with a decision, open an RFC -- don't silently change behavior.

---

### AD-001: `src` layout for Python packaging
**Date:** Project start
**Decision:** Use `src/agentharness/` not flat `agentharness/` at root.
**Why:** Prevents editable-install import confusion, enforces that tests actually import from the installed package not the local directory, standard for PyPI-distributed packages as of 2024. hatch, flit, and setuptools all handle it cleanly.
**Trade-off:** Slightly unfamiliar to engineers used to flat layouts. Minor.

---

### AD-002: Tool intercept via wrapper, not monkey-patching

**Archival (Phase 0 original wording -- superseded April 2026):**

~~**Date:** Phase 0~~  
~~**Decision:** Intercept tool calls by wrapping the callable at scenario setup time, not by monkey-patching framework internals.~~  
~~**Why:** Monkey-patching LangGraph/CrewAI internals means every framework version change breaks us. Wrapper approach is stable: we give the adapter a tool registry, the adapter swaps real tools for wrapped versions before running the scenario, and we swap back after.~~  

*(Complete prior AD-002 including the original `wrap_tool` code sample: [project_context_revisions.md](project_context_revisions.md), entry 2026-04-19.)*

**Current:**
**Date:** Phase 0 (updated April 2026 after LangGraph validation)
**Decision:** Intercept tool calls without monkey-patching framework internals. The exact hook is **framework-specific**; LangGraph has a first-class API we use as primary, with tool replacement as fallback.
**Why:** Monkey-patching LangGraph/CrewAI internals means every framework version change breaks us. Public wrapper APIs and explicit tool substitution are stable: the adapter either uses the framework's supported interception surface or swaps tools before execution, then restores after the scenario.
**LangGraph (validated April 2026):**
- **Primary:** `ToolNode(..., wrap_tool_call=..., awrap_tool_call=...)`. LangGraph passes each execution a `ToolCallRequest` and an `execute` callable; our bridge lives in `src/agentharness/adapters/langgraph.py` (`make_sync_wrapper`, `make_async_wrapper`, `create_intercepted_tool_node`). No LangGraph source patching.
- **Fallback (same AD-002 spirit):** Replace tools with `StructuredTool.from_function` preserving name, description, and `args_schema` (`make_replacement_tool`, `create_intercepted_tool_node_fallback`) for stacks that lack the wrapper parameters or when we need identical behavior without touching `ToolNode` kwargs.
**Framework-agnostic core:** `HarnessInterceptor` in `src/agentharness/mocks/interceptor.py` records calls and routes MOCK vs LIVE; adapters only translate framework types to/from that core.
**Generic mental model (non-LangGraph adapters still follow this shape):**
```python
def wrap_tool(real_fn, recorder):
    def wrapped(*args, **kwargs):
        recorder.record_call(real_fn.__name__, args, kwargs)
        return recorder.get_response(real_fn.__name__, args, kwargs)
    return wrapped
```
**Trade-off:** Each adapter must implement correct wiring. OpenAI / Anthropic / CrewAI will not use `ToolNode`; they get their own adapter modules. We test each adapter independently.

---

### AD-003: OpenInference-compatible trace schema, not proprietary
**Date:** Phase 0
**Decision:** The trace schema uses OpenInference attribute names as the base, extended with harness-specific fields under the `harness.*` namespace.
**Why:** OpenInference is Apache 2.0 and is already supported by Arize Phoenix, LangFuse (partial), and W&B Weave. Building on it means every trace we produce is immediately readable by these tools. It also aligns with OpenTelemetry's experimental gen_ai.* semantic conventions.
**Key schema fields:**
```json
{
  "trace_id": "uuid-v4",
  "harness.scenario_id": "string",
  "harness.mode": "mock | live | record | replay",
  "harness.seed": "integer | null",
  "gen_ai.system": "openai | anthropic | langgraph | ...",
  "gen_ai.request.model": "string",
  "spans": [...]
}
```
**Full schema:** see `src/agentharness/telemetry/schema.py`

---

### AD-004: Pytest as the primary runner
**Date:** Phase 0
**Decision:** Scenarios are Python files with `def test_*(scenario):` functions, run by pytest via a `pytest-agentharness` plugin.
**Why:** Engineers already know pytest. CI systems already run pytest. Zero new tooling required for CI integration. Assertions become standard pytest failures. IDE support (run in VS Code, PyCharm) is free.
**How it works:**
```python
from agentharness import assert_called_before, assert_arg_lte, scenario

@scenario("scenarios/refund_happy_path.yaml")
def test_refund_happy_path(run):
    assert_called_before(run.trace, "lookup_order", "issue_refund")
    assert_arg_lte(run.trace, tool="issue_refund", arg="amount", value=100)
```
*(Phase 0: `run` is wired; `assert_arg_lte` and full scenario YAML execution are Sprint 2+ unless noted elsewhere.)*
**Trade-off:** Users who don't use pytest need to use the CLI runner instead. Acceptable -- CLI is also supported.

---

### AD-005: Mock mode is always the default, cassettes are sanitized by default
**Date:** Phase 0
**Decision:** Unless `mode="live"` is explicitly set and `--allow-real-tools` flag is passed to the CLI, all tool calls are intercepted and no real network calls are made. Cassettes saved via `agentharness record` apply PII and secret scrubbing by default before writing to disk.
**Why:** A test that accidentally emails a real customer, charges a real card, or deletes a real database record is a catastrophic failure. Safe by default is non-negotiable. The friction of opting into live mode is intentional. Similarly, cassettes that are intended for version control must be sanitized to prevent committing sensitive data.
**How it works:** The Environment object checks mode before every tool execution. If mode is `mock` and no mock response is configured for the called tool, it raises `MockNotConfiguredError` rather than calling the real function. This is a loud failure, not a silent pass-through. Cassette save path runs through the sanitization pipeline (secret scrubbing always on, PII scrubbing on by default) before writing. Use `--allow-sensitive-recording` to bypass PII scrubbing with a CLI warning.

---

### AD-006: Apache 2.0 license
**Date:** Project start
**Decision:** Apache 2.0.
**Why:** Enterprise-friendly (explicit patent grant), OSI-approved, compatible with MIT and other Apache libraries we depend on (OpenInference, OTel). Does not restrict commercial use. Does not require commercial users to open-source their derivative works. BSL and AGPL were considered and rejected -- both create community trust problems for a framework trying to be the neutral player.

---

### AD-007: Python 3.10+ minimum version
**Date:** Phase 0
**Decision:** Minimum Python version: 3.10. Target: 3.11 and 3.12.
**Why:** 3.10 brings match/case (used for trace event routing), 3.10+ has better type hint syntax. 3.9 EOL is October 2025. Most agent framework dependencies (LangGraph 0.3+, CrewAI 0.9+) also require 3.10+.
**Trade-off:** Excludes users on 3.9. Acceptable given the target audience is teams actively building production agents in 2026.

---

### AD-008: Local-first trace storage, optional backend export
**Date:** Phase 0
**Decision:** By default, traces are stored as `.jsonl` files in a local `.agentharness/traces/` directory within the project. Export to external backends (LangFuse, Arize Phoenix, OTLP) is optional and configurable.
**Why:** Zero dependencies on external services for the OSS tier. Teams working in air-gapped environments or with strict data residency requirements should not be forced to send data anywhere.
**Storage path:** `.agentharness/traces/YYYY-MM-DD/scenario_name_TIMESTAMP.jsonl`
**Note:** `.agentharness/` should be in `.gitignore` unless users explicitly want to commit traces (cassettes, which are smaller, deterministic, and sanitized, can be committed).

---

### AD-009: Approval gate binding with structured artifacts
**Date:** Phase 0
**Decision:** Approval artifacts must be cryptographically or structurally tied to: tool name, normalized arguments hash, actor identity, timestamp/expiry, and scenario/run ID.
**Why:** `approval_before_destructive()` is necessary but not sufficient if the approval artifact is unbounded. An "approve_refund" decision in one concurrent run should not inadvertently authorize a different refund in another run. Binding the approval to the specific tool call's args hash and run ID prevents cross-run authorization leakage.
**Trade-off:** Slightly more complex approval gate implementation. Worth it for correctness in concurrent/multi-agent scenarios.

---

### AD-010: Emergency stop operates at three defined tiers
**Date:** Phase 0
**Decision:** Emergency stop has three tiers with explicit latency expectations:
- **SOFT** (orchestrator interrupt, e.g. LangGraph `interrupt()`): under 500ms -- guaranteed
- **HARD** (SIGTERM, escalating to SIGKILL after 3s): under 500ms for signal delivery -- guaranteed
- **ABORT** (HARD + best-effort state checkpoint if checkpointing enabled): latency depends on checkpoint size

**Why:** "Emergency stop within 500ms" cannot be guaranteed universally. An in-flight HTTP call already dispatched to an external API cannot be recalled. Defining three tiers with explicit guarantees prevents overclaiming. SIGKILL cannot be caught and there is no rollback after SIGKILL -- ABORT mode is best-effort checkpoint, not rollback.

---

### AD-011: Harness assertions return `AssertionResult` (compliance-oriented, pytest-compatible)
**Date:** April 2026
**Decision:** Public helpers in `assertions/structural.py`, `argument.py`, `safety.py`, and `resource.py` return an `AssertionResult` dataclass (`assertions/base.py`). Required fields include `passed`, `assertion_name`, `tool` (or `None` for trace-wide checks), `message`, `regulatory_refs`, and `details`. Regulatory strings are **not** inlined per call site; they are taken from `REFS_*` tuples in `base.py` so mappings stay consistent for compliance reporting. On `passed=False`, `finish()` is the single code path that raises `AssertionError(result.message)` (optional `__cause__` for schema validation failures), preserving standard pytest output; `ValueError` remains the contract for invalid inputs (e.g. bad regex, negative thresholds where forbidden). **Collection:** a module-level `ContextVar` (`_results_collector`) receives a copy of every `AssertionResult` before any raise when `set_results_collector` has bound a list (used by `agentharness run`); pytest tests rely on the bound pytest item stash (`bind_pytest_item`) plus `LOGREPORT_PENDING` unless that ContextVar is also set — no monkey-patching of `finish` imports per assertion module (KI-007).
**Why:** Future console reporters and PDF/HTML evidence generators need structured outcomes plus citeable regulatory anchors without re-parsing exception strings. Test authors still get immediate failures in CI. `details` holds tool names, observed call order, numeric bounds, and short `constraint` descriptions so formatters do not import assertion module internals.
**Trade-off:** Callers must tolerate a return value instead of `None`; type hints now return `AssertionResult`. Downstream IDEs and composable test helpers can consume the record intentionally.

---

## INTEGRATIONS & DEPENDENCIES

### Direct Dependencies (always installed)
| Package | Version Constraint | Why |
|---|---|---|
| `opentelemetry-sdk` | >=1.20 | Trace capture and OTLP export |
| `opentelemetry-semantic-conventions` | >=0.41 | Standard gen_ai.* attribute names |
| `pydantic` | >=2.0 | Scenario + Trace schema validation |
| `pytest` | >=7.0 | Test runner |
| `rich` | >=13.0 | Terminal output formatting |
| `httpx` | >=0.27 | HTTP mocking for tool calls |
| `jsonschema` | >=4.0 | Argument schema validation (Test 2.3) |

### Optional Dependencies (installed as extras)
| Extra | Packages | When Needed |
|---|---|---|
| `[dev]` | `pytest-asyncio` | Async unit tests (`@pytest.mark.asyncio`); e.g. `pip install -e ".[langgraph,dev]"` |
| `[langgraph]` | `langgraph`, `langchain-core` | LangGraph adapter |
| `[openai]` | `openai` | OpenAI SDK adapter |
| `[anthropic]` | `anthropic` | Anthropic SDK adapter |
| `[crewai]` | `crewai` | CrewAI adapter |
| `[live]` | `textual`, `fastapi`, `uvicorn` | Live Mode |
| `[compliance]` | `jinja2`, `weasyprint` | PDF report generation |
| `[langfuse]` | `langfuse` | LangFuse export |
| `[arize]` | `arize-phoenix`, `openinference-semantic-conventions` | Arize export |

### Install Examples
```bash
pip install agentharness                          # Core only
pip install "agentharness[langgraph,openai]"      # Common stack
pip install "agentharness[langgraph,compliance]"  # With EU AI Act reports
pip install -e ".[langgraph,dev]"                 # Local dev: LangGraph + async pytest
pip install "agentharness[all]"                   # Everything (includes dev extra)
```

---

### OSS Repos We Incorporate

| Repo | License | How We Use It |
|---|---|---|
| `Arize-ai/openinference` | Apache 2.0 | **Direct dependency**: trace schema base + auto-instrumentation |
| `langchain-ai/agentevals` | MIT | **Incorporate**: trajectory matching evaluators, decoupled from LangSmith |
| `confident-ai/deepeval` | Apache 2.0 | **Incorporate**: ToolCorrectnessMetric, TaskCompletionMetric implementations |
| `AgentOps-AI/tokencost` | MIT | **Direct dependency**: LLM cost estimation |
| `UKGovernmentBEIS/inspect_ai` | MIT | **Borrow patterns**: sandboxing architecture, VS Code viewer frontend (Phase 2+) |
| `promptfoo/promptfoo` | MIT | **Borrow patterns**: YAML scenario schema design, CI integration patterns |
| `AgentOps-AI/agentops` | MIT | **Borrow patterns**: session replay UX design |

**Arize Phoenix licensing note:** Arize Phoenix's self-hosted product is under ELv2 (Elastic License 2.0), not a permissive OSS license. This does not block our trace export integration (the OpenInference schema is Apache 2.0 and Phoenix consumes OTLP), but we should not describe the entire Arize ecosystem as "uniformly permissive."

**Clean room rule:** If we borrow patterns (not code), implement fresh. If we incorporate (use actual code), use as a direct dependency or fork under its original license terms. Never copy code and remove attribution.

---

## KEY FILE LOCATIONS

```
src/agentharness/core/scenario.py       -> Scenario DSL -- start here to understand data model
src/agentharness/core/trace.py          -> Trace schema -- start here to understand output format
~~src/agentharness/mocks/interceptor.py   -> Tool intercept -- the most critical piece of Phase 0~~
src/agentharness/mocks/interceptor.py   -> HarnessInterceptor + ToolCallRecord -- framework-agnostic intercept core
src/agentharness/adapters/langgraph.py  -> LangGraph ToolNode wiring (native wrap_tool_call + AD-002 fallback)
src/agentharness/adapters/base.py       -> FrameworkAdapter contract -- implement this for new adapters
src/agentharness/assertions/safety.py   -> Most important assertions (approval gate, PII, loop)
src/agentharness/pytest_plugin.py       -> Pytest plugin: `run` fixture, marker registration (pytest11 entry point)
src/agentharness/reporting/console.py  -> ConsoleReporter; formats AssertionResult for terminal output; called by pytest plugin hooks and `agentharness run` CLI
src/agentharness/cli/run.py            -> `agentharness run` subcommand; loads scenario YAML, runs via `core/runner.py`, formats output via `ConsoleReporter`
src/agentharness/scenario.py            -> `@scenario` decorator (AD-004)
src/agentharness/telemetry/jsonl.py -> Trace JSONL read/write (AD-008); import from `telemetry.jsonl`, not `telemetry` package root
src/agentharness/telemetry/collector.py -> TraceCollector; converts ToolCallRecord → Span → Trace; import from `agentharness.telemetry.collector` not package root
tests/unit/test_langgraph_intercept.py  -> Proof that ToolNode interception works (sync/async, both strategies)
examples/01_customer_support_langgraph/ -> Phase 0 LangGraph refund example (5 YAML scenarios, mock tools, `support/executor.py`); must always run cleanly with `pytest`
scenarios/safety/                       -> Built-in safety scenarios; free for community to use
docs/guides/eu_ai_act.md               -> Primary compliance documentation
docs/compliance/colorado_sb24_205.md    -> Colorado SB 24-205 compliance guide
.github/workflows/ci.yml               -> What must pass for a PR to merge
pyproject.toml                          -> All dependencies and tool configuration
```

---

## KNOWN ISSUES & TECHNICAL DEBT

> Log issues here as they are discovered. Move to GitHub Issues for tracking. Don't let this list grow stale -- review and clean it at the start of each phase.

| ID | Issue | Severity | Status | Notes |
|---|---|---|---|---|
| KI-001 | ~~LangGraph ToolNode interception approach not yet validated against LangGraph 0.4.x~~ **Now:** LangGraph ToolNode interception without patching internals | HIGH | ~~OPEN~~ **RESOLVED** | ~~Must resolve in Phase 0 Sprint 1. If it doesn't work, architecture needs revision. Document fallback plan.~~ **Now:** Validated April 2026 on `langgraph` 1.1.8 / `langgraph-prebuilt` 1.0.10 / `langchain-core` 1.3.0 (Python 3.14 smoke test; project target remains 3.10--3.12 per AD-007). Primary: `wrap_tool_call` / `awrap_tool_call`. Fallback: tool replacement (`create_intercepted_tool_node_fallback`). Evidence: `tests/unit/test_langgraph_intercept.py` (8 tests). Historical note: issue text referenced "0.4.x"; current packages use prebuilt versioning -- track `langgraph-prebuilt` for the `ToolNode` API. |
| KI-002 | Cassette format needs handling for non-deterministic tool argument ordering (dict key order) | MEDIUM | OPEN | Arguments should be hashed after normalizing key order. |
| KI-003 | PII detection regex approach will have false positives on numerical data | LOW | OPEN | Flag for human review rather than hard failure. Make configurable. |
| KI-004 | Token cost estimation requires tokencost library to be updated when new models release | LOW | ONGOING | Pin tokencost version; update at each release. Do not state "400+ models" as a static fact. |
| KI-005 | ~~Async tool interception is unaddressed in Phase 0 design~~ **Now:** Async tool interception alongside sync | HIGH | ~~OPEN~~ **RESOLVED** | ~~LangGraph natively supports async tools. The async wrapper design (handling `async def` tools with proper `await`) must be validated in Phase 0 alongside the sync case.~~ **Now:** Same validation run as KI-001: `test_async_mock_mode`, `test_async_live_mode` (native wrapper), `test_fallback_async_mock_mode` (AD-002). `HarnessInterceptor.intercept_async` + `awrap_tool_call` bridge is the pattern. |
| KI-006 | Cassette sanitization must be default-on for PII/secrets before version-control commit | MEDIUM | OPEN | See AD-005. Default behavior: PII scrubbing on in compliance mode; secret scrubbing always on. `--allow-sensitive-recording` flag for bypass. |
| KI-007 | ~~`cli/run.py` per-module `finish()` patching violated AD-011 and would silently miss results from `argument.py`, `safety.py`, `resource.py`~~ | HIGH | **RESOLVED** | Fixed by `_results_collector` `ContextVar` in `assertions/base.py` with `set_results_collector` / `reset_results_collector`; `finish()` appends before raise; CLI binds the list for scenario assertions; pytest uses stash only (documented on `pytest_plugin.py`). |

---

## PHASE 0 SPRINT PLAN

### Sprint 1: Core Plumbing

**Goal:** Tool intercept works (sync + async). Trace captures a LangGraph run. One structural assertion passes in pytest.

| Task | Owner | Status | Notes |
|---|---|---|---|
| Validate LangGraph ToolNode wrapping approach (sync) | Engineer 1 | ~~TODO~~ **DONE** | ~~See KI-001 -- this is the critical path~~ KI-001; native + fallback covered in `test_langgraph_intercept.py` |
| Validate LangGraph ToolNode wrapping approach (async) | Engineer 1 | ~~TODO~~ **DONE** | ~~See KI-005 -- must validate alongside sync~~ KI-005; async native + fallback covered |
| Define Span and Trace dataclasses | Engineer 1 | ~~TODO~~ **DONE** | `core/trace.py` (`Trace`, `Span`), `telemetry/schema.py` (keys); tests: `tests/unit/test_trace_models.py`. Collector / JSONL next. |
| Implement `interceptor.py` core | Engineer 1 | ~~TODO~~ **DONE** | ~~Mock mode only first. Both sync and async.~~ `HarnessInterceptor`, MOCK/LIVE, sync/async; `MockNotConfiguredError` per AD-005 |
| Wire LangGraph adapter (`adapters/langgraph.py`) | Engineer 1 | **DONE** | *(Row added 2026-04-19.)* Native wrappers + fallback; documented in AD-002 |
| Implement `assert_called_before` | Engineer 2 | **DONE** | `assertions/structural.py`; tests `tests/unit/test_assert_called_before.py`; exported from `agentharness` and `agentharness.assertions`. |
| Pytest plugin skeleton | Engineer 2 | **DONE** | `pytest_plugin.py`: `run` fixture + `agentharness_scenario` marker; `scenario.py`: `@scenario` decorator; `core/runner.py` `run_scenario()` (Phase 0 shell trace). Entry point `pytest11` → `agentharness.pytest_plugin`. Tests: `tests/unit/test_pytest_plugin.py`; `tests/conftest.py` enables `pytester` for plugin tests. |
| `pyproject.toml` setup | Engineer 2 | ~~TODO~~ **DONE** | Dependencies, entry points, test config; UTF-8 encoding verified |
| GitHub Actions CI basic | Engineer 2 | **DONE** | `.github/workflows/ci.yml`: PR + push to `main`/`master`; matrix Python 3.10–3.12; `pip install -e ".[langgraph,dev]"`; `python -m pytest tests/unit/ -v`. |
| Document fallback architecture plan for KI-001 | Engineer 1 | ~~TODO~~ **DONE** | ~~What if ToolNode wrapping requires revision?~~ Implemented as `create_intercepted_tool_node_fallback` + tests; AD-002 updated |

**Sprint 1 Exit Criteria:**
```python
# This test must pass in GitHub Actions:
from agentharness import assert_called_before, scenario

@scenario("scenarios/refund_happy_path.yaml")
def test_lookup_called_before_refund(run):
    assert_called_before(run.trace, "lookup_order", "issue_refund")
```

**Evidence:** `tests/unit/test_sprint1_exit_criteria.py` matches this snippet and is part of `pytest tests/unit/` (CI). `scenarios/refund_happy_path.yaml` declares `tool_calls`; `run_scenario()` in `core/runner.py` loads YAML and records synthetic tool calls via `HarnessInterceptor.record_call` → `TraceCollector` in that order.

---

### Sprint 2: Phase 0 Completion

**Goal:** All Phase 0 deliverables. Customer support example fully working.

| Task | Owner | Status | Notes |
|---|---|---|---|
| `assert_call_count`, `assert_completion`, `assert_mutual_exclusion` | Engineer 1 | **DONE** | `assertions/structural.py`; tests `tests/unit/test_structural_batch.py`; exported from `agentharness` / `agentharness.assertions`. |
| `assert_arg_lte`, `assert_arg_pattern`, `assert_arg_schema`, `assert_arg_not_contains` | Engineer 2 | **DONE** | `assertions/argument.py`; tests `tests/unit/test_argument_assertions.py`; `jsonschema` for schema validation. |
| `assert_approval_gate`, `assert_no_loop` | Engineer 1 | **DONE** | `assertions/safety.py`; tests `tests/unit/test_safety_assertions.py`. Approval: `approved` / `approval_id` on tool args (Phase 0); refine with AD-009. |
| `assert_cost_under` + tokencost integration | Engineer 2 | **DONE** | `assertions/resource.py`; `harness.estimated_cost_usd` or token counts + optional `tokencost`; tests `tests/unit/test_resource_assertions.py`; extra `resource` / `tokencost` in `dev`. |
| Trace JSONL serialization | Engineer 1 | **DONE** | `telemetry/jsonl.py` (`trace_to_jsonl_line`, `write_trace_jsonl`, `iter_traces_jsonl`, AD-008 `default_trace_path` / `write_trace_to_default_location`). Not re-exported from `telemetry/__init__.py` (avoids circular import with `core.trace`). Tests: `tests/unit/test_trace_jsonl.py`. |
| Console reporter (pytest-style output) | Engineer 2 | **DONE** | `reporting/console.py` (`ConsoleReporter`, rich with plain fallback); `pytest_runtest_logreport` / `pytest_runtest_makereport` / `pytest_terminal_summary` in `pytest_plugin.py`; `LOGREPORT_PENDING` + item stash in `assertions/base.py`; tests `tests/unit/test_console_reporter.py`. |
| Example 01: Customer support refund agent | Engineer 1 | **DONE** | `examples/01_customer_support_langgraph/`: `support/refund_tools.py` (6 mock tools), `support/executor.py` (LangGraph ``ToolNode`` + interceptor, YAML ``steps``), 5 scenarios under `scenarios/`, `test_refund_agent.py`, README; local ``run`` fixture. |
| `agentharness run` CLI command | Engineer 2 | **DONE** | `cli/main.py` (argparse group + stubs), `cli/run.py` (YAML + `run_scenario` + `harness.mode`, `set_results_collector` + `ConsoleReporter`); `[project.scripts]` → `cli:cli`; Phase 0 exit: `scenarios/safety/refund_limit_guard.yaml`; tests `tests/unit/test_cli_run.py`. |
| README first draft | Both | **DONE** | Root `README.md`: install (`pip install -e .` / `.[langgraph,dev]` + extras pointer), quickstart (example `test_happy_path`), assertion table from `REFS_*`, CLI one-liner, roadmap (text only; no `Founder_Docs/` link), license, contributing pointer. |
| Phase 0 exit review | Both | **DONE** | Exit review 2026-04-19: Sprint 1 criterion test passes; examples + 67 unit tests + CLI `run` + CI matrix + AD-002 fallback + KI-001/005/007 evidence verified; `pip install -e ".[langgraph,dev]"` OK; `Span.status_code` default set for mypy (`core/trace.py`). |

**Phase 0 Exit Criteria:**
- `examples/01_customer_support_langgraph/` runs cleanly with `pytest`
- `agentharness run scenarios/safety/refund_limit_guard.yaml` produces pass/fail output
- GitHub Actions CI passes (unit tests only)
- KI-001 and KI-005 resolved (LangGraph intercept approach confirmed for sync and async)
- `pip install agentharness` works locally (no PyPI publish yet -- local install only)
- Fallback architecture plan documented

---

## PHASE 1 BACKLOG (Not Yet Scheduled)

Items confirmed for Phase 1 but not yet sprint-planned. Ordering reflects priority.

1. ~~Record mode + cassette file format (with default sanitization per AD-005)~~ **Checkpoint 1**
2. ~~Replay mode (deterministic re-run from cassette)~~ **Checkpoint 1**
3. ~~Regression diff engine~~ **Checkpoint 1**
4. OpenAI Responses API adapter (primary; legacy Assistants API support as migration path only -- sunset August 26, 2026)
5. Multi-run statistical mode (`--runs N`)
6. Safety assertions: `assert_pii_clean`, `assert_permission_boundary`
7. LangFuse export integration
8. Arize Phoenix export integration
9. CrewAI adapter
10. PyPI public release (0.1.0)
11. Documentation site (mkdocs + GitHub Pages)
12. Public launch (HN, Discord, blog post)

---

## PHASE 1 SPRINT PLAN

### Checkpoint 1: Record, Replay, Diff

**Goal:** A team can record a known-good agent run, commit the cassette, and get a regression alert in CI when behavior changes. First installable alpha on PyPI.

| Task | Owner | Status | Notes |
|---|---|---|---|
| .gitattributes + LF normalization | Engineer 2 | **DONE** | Enforces LF repo-wide via `.gitattributes`; `git add --renormalize .` applied; resolves LF→CRLF Git warnings on Windows. *(Infrastructure add-on before collector work; not in original sprint plan.)* |
| .editorconfig + ruff in CI | Engineer 2 | **DONE** | Root `.editorconfig` (UTF-8, LF, trim rules; `.md` no trim); `[dev]` + `ruff>=0.4.0`; `[tool.ruff]` line-length 88, lint E/F/W/I (E501 ignored until docstring wrap); `[tool.ruff.format]`; parallel `lint` job in `ci.yml` (`pip install -e ".[dev]"`, `ruff check` / `ruff format --check` on `src/`). `extend-exclude`: `assertions` + `adapters` only (`telemetry/collector.py` linted). |
| telemetry/collector.py | Engineer 1 | **DONE** | `TraceCollector` in `telemetry/collector.py`; `record()` → TOOL spans (`tool.name`, `input.value`, `output.value`); `core/runner.py` + example `executor.py` wire `HarnessInterceptor.record_call` → collector; tests `tests/unit/test_collector.py` |
| mocks/cassette.py | Engineer 1 | TODO | Cassette read/write; sha256(tool_name + sorted_args_json) key per DOMAIN KNOWLEDGE; secret scrubbing always on, PII scrubbing default per AD-005; closes KI-002 and KI-006 |
| cli/record.py — agentharness record | Engineer 1 | TODO | Live run → sanitized cassette; --allow-sensitive-recording flag per AD-005 |
| Replay mode — agentharness run --replay | Engineer 2 | TODO | Deterministic re-run from cassette; zero variance across 10 runs of same cassette |
| reporting/diff.py — regression diff | Engineer 2 | TODO | Structural diff between two traces; human-readable output per reporting/ pattern |
| Update example 01 to use collector | Engineer 1 | **DONE** | `support/executor.py` uses `TraceCollector`; `trace_builder.py` stubbed (replaced by collector) |
| PyPI 0.1.0-alpha prep | Both | TODO | Version bump in pyproject.toml; confirm pip install agentharness==0.1.0a1 works from PyPI |

**Checkpoint 1 Exit Criteria:**

- `agentharness record scenarios/safety/refund_limit_guard.yaml` produces a sanitized cassette file
- `agentharness run --replay <cassette>` produces identical pass/fail output across 10 runs
- `agentharness run --replay <cassette> --diff <cassette2>` produces human-readable diff output
- `pip install agentharness==0.1.0a1` works from PyPI
- All existing unit tests still pass
- KI-002 and KI-006 resolved

### Checkpoint 2 and Checkpoint 3

Not yet sprint-planned. See PHASE 1 BACKLOG for confirmed items.

---

## DOMAIN KNOWLEDGE

> Things that took effort to learn and will save time for the next person.

### On LangGraph Tool Interception
~~LangGraph executes tools via `ToolNode`, which calls the tool's `invoke()` method. The cleanest interception point is at tool instantiation: replace the tool's wrapped function with a harness wrapper before passing the tool list to `StateGraph`. This avoids patching LangGraph internals. The wrapper must preserve the tool's name, description, and schema (used by the LLM) while replacing only the execution path. Both sync and async tools must be handled.~~ *(Prior paragraph + original `make_mock_tool` sample: [project_context_revisions.md](project_context_revisions.md) 2026-04-19; the code pattern remains below as "Older mental model".)*

**Discovery (April 2026):** `ToolNode` exposes first-class interception via `wrap_tool_call` (sync) and `awrap_tool_call` (async). Each invocation receives a `ToolCallRequest` (tool name, args, id, tool object, state, runtime) and an `execute(request)` callable that runs the real tool path. This is the **primary** integration surface -- no monkey-patching of LangGraph, no replacement of internal methods.

**Our bridge:** `src/agentharness/adapters/langgraph.py` builds wrappers that call `HarnessInterceptor.intercept_sync` / `intercept_async`. In MOCK mode the interceptor returns canned data and synthesizes a `ToolMessage`; in LIVE mode it delegates to `execute` / `await execute` so the real tool runs and the result is recorded.

**Standalone / test `invoke`:** When calling `ToolNode.invoke` or `ainvoke` **outside** a compiled graph, LangGraph still expects a runtime object in config. Pass:
```python
from langgraph.runtime import Runtime
config = {"configurable": {"__pregel_runtime": Runtime()}}
tool_node.invoke(tool_calls, config=config)
```
Without this, RunnableCallable raises `ValueError: Missing required config key ... for 'tools'`. Full graphs inject this automatically.

**Return shape:** For direct tool-call list input, `ToolNode` returns a **dict** `{"messages": [ToolMessage, ...]}` (not a bare list). Tests must index `result["messages"]`.

**Fallback (AD-002):** If `wrap_tool_call` is unavailable on an old `langgraph-prebuilt`, use `make_replacement_tool` + `create_intercepted_tool_node_fallback` -- rebuild each `BaseTool` with `StructuredTool.from_function` preserving `args_schema`, name, and description. Validated in the same test module.

**Validated versions:** `langgraph` 1.1.8, `langgraph-prebuilt` 1.0.10, `langchain-core` 1.3.0. Pin minimum versions in packaging once we define a support matrix; do not assume the historical "LangGraph 0.4.x" version string from early notes -- track **`langgraph-prebuilt`** for `ToolNode` API compatibility.

**Older mental model (still valid for fallback and for other frameworks):** replace the tool's execution path at instantiation while preserving schema metadata:

```python
def make_mock_tool(original_tool, mock_registry):
    @tool(original_tool.name, description=original_tool.description)
    def mocked(**kwargs):
        return mock_registry.get_response(original_tool.name, kwargs)
    return mocked
```

### On Non-Determinism
LLM outputs are stochastic. The same scenario run 10 times may produce 10 different action traces. The harness handles this in three layers:
1. **Replay mode**: use a recorded cassette -- the LLM is never called, so there is zero variance in tool responses. Note: for fully deterministic replay, a mock LLM must also be configured, since LLM outputs captured in Record mode are not deterministic across model versions, inference providers, or floating-point hardware differences.
2. **Temperature=0**: where supported, set temperature=0 to minimize (not eliminate) variance
3. **Statistical mode**: run N times, report pass@k and distribution. Set assertions as "must pass 8 of 10 runs."
Do not pretend non-determinism doesn't exist. A test that passes 9/10 times is a test with a known 10% failure rate, not a "flaky test."

### On EU AI Act Article 12 Logging Requirements
Article 12 requires *automatic* logging -- not logging you remember to turn on. The harness's trace collector must be the automatic logging layer. The compliance report generator then verifies that every required field is present in every trace.

Specific minimum logging fields vary by system category. The most prescriptive requirements (reference database, input data that led to a match, identity of natural persons verifying results) apply to Annex III point 1(a) biometric identification systems. For general high-risk systems, Article 12 requires automatic logging to support traceability, but finalized technical standards (prEN 18229-1, ISO/IEC DIS 24970) are still in draft. Our implementation follows best-practice interpretation pending these standards.

### On EU AI Act Digital Omnibus
As of April 2026, the Digital Omnibus proposal (published November 19, 2025) proposes delaying Annex III high-risk obligations from August 2, 2026 to December 2, 2027. The European Parliament voted 569-45 in favor on March 26, 2026; trilogue is targeting agreement by late April 2026. Until formally enacted, August 2, 2026 remains the legal deadline. Build for August 2026; plan for the likely delay.

### On Cassette Design
Cassettes must be:
- **Deterministic**: given the same arguments, always return the same response
- **Human-readable**: engineers need to be able to read and edit cassettes
- **Version-controlled**: committed to the repo alongside scenario files
- **Compact**: don't store the full response object when a summary suffices
- **Sanitized**: PII and secrets scrubbed before save by default

The cassette key is `sha256(tool_name + sorted_args_json)`. This ensures argument ordering doesn't affect cassette lookups. Consider extending the key with tool version/implementation fingerprint, schema version, and scenario version for stronger replay determinism across version changes. Dynamic values (timestamps, IDs) should be configurable as "frozen" in the cassette.

### On the Approval Gate Pattern (LangGraph)
LangGraph's `interrupt()` function pauses graph execution at a specific node. The caller receives interrupt data via `["__interrupt__"]` key. When ready, the caller invokes the graph again with `Command(resume=...)`. This is the native mechanism for human-in-the-loop. In test mode, the harness intercepts interrupt events and applies the configured policy (auto-approve, auto-reject, or record the interrupt for assertion checking). In Live Mode, the harness surfaces the interrupt to the operator UI and waits for a real decision. Approval artifacts must be bound to tool name, args hash, actor, timestamp, and run ID (see AD-009).

### On the OpenAI Responses API Migration
The OpenAI Assistants API was deprecated on August 26, 2025, with full shutdown scheduled for August 26, 2026. The replacement is the Responses API (for execution) combined with the Conversations API (for state management). Key migration considerations:
- Prompts replace Assistants (but can only be created via dashboard, not programmatically)
- Conversations replace Threads
- Responses replace Runs
- Items replace Run Steps
- Response objects have a 30-day TTL
Our Phase 1 OpenAI adapter targets the Responses API as the primary interface. Legacy Assistants API support is available as a migration path only.

---

## SECURITY & SECRETS

### Never Do These
- Never log real API keys, tokens, or secrets in trace files
- Never commit real credentials to the repository
- Never let cassette files contain real PII from live runs (unless `--allow-sensitive-recording` explicitly used)
- Never call real external APIs in unit or integration tests

### How Secrets Are Handled
- Secrets in test scenarios are configured via environment variables, never hardcoded
- The trace schema has a `secrets_scrubbed: true` flag; the trace serializer replaces configured secret patterns with `[REDACTED]` before writing
- PII scrubbing in traces is on by default in compliance mode; the compliance report flags if it's disabled
- Secret scrubbing cannot be disabled

### Security Disclosure
Report vulnerabilities via SECURITY.md instructions. Include: disclosure policy, security contact email, expected response timeline (target: 72 hours to acknowledge, 30 days to fix for critical vulnerabilities). Do not open public GitHub issues for security bugs.

---

## CONTRIBUTION PROCESS

### For Core Team
1. Work in feature branches: `feature/`, `fix/`, `docs/`, `chore/`
2. Every PR must pass CI (all unit tests, integration tests where not mock-breaking)
3. Every public function needs a docstring before merge
4. Update this file when you make an architectural decision or discover something important (use ~~strikethrough~~ for replaced fragments and append [project_context_revisions.md](project_context_revisions.md))
5. Code review: minimum 1 reviewer for any change; 2 reviewers for changes to assertions or trace schema

### Windows: UTF-8 for `.py` files and repo Markdown (pytest collection)

PowerShell's `Write-Output`, here-strings piped to `Set-Content`, and some editor save paths on Windows default to **UTF-16 LE** (often with BOM). Python source must be **UTF-8**. A test module saved as UTF-16 can fail collection with an opaque error such as `SyntaxError: source code string cannot contain null bytes` (pytest's AST parse sees the interleaved zero bytes as "null characters"). **Fix:** write or re-save test and source files as **UTF-8** explicitly (e.g. `Set-Content -Encoding utf8`, `open(path, "w", encoding="utf-8")`, or the editor encoding selector). Prefer **UTF-8 without BOM** for `.py` files when the toolchain allows it; UTF-8 with BOM is acceptable for Python 3. If collection fails on a new file, inspect the raw bytes: UTF-16 LE often starts with a **BOM** (hex `FF FE`) or shows **null bytes** between ASCII characters in a hex editor.

**Cursor / editor Write and StrReplace on this machine:** Those code paths have repeatedly produced **UTF-16** for touched files. This is a **documented pattern on this specific machine**, not a hypothetical warning. Files that have already been hit include: `src/agentharness/core/__init__.py`, `tests/unit/test_assert_called_before.py`, `src/agentharness/scenario.py`, `src/agentharness/pytest_plugin.py`, `tests/unit/test_pytest_plugin.py`, `tests/unit/test_argument_assertions.py`, `tests/unit/test_resource_assertions.py`, `tests/unit/test_safety_assertions.py`, `README.md`, and `CHANGELOG.md`. Repository Markdown is not exempt: the same UTF-16 LE pattern (null bytes between characters, or leading `FF FE`) and the same fix apply—decode and re-save as **UTF-8 without BOM** (e.g. `Path.read_bytes().decode("utf-16-le")` then `write_text(..., encoding="utf-8")`, or `[System.IO.File]::WriteAllText` with `UTF8Encoding` constructed without BOM). **Before running pytest** after an agent or local edit, confirm the file is UTF-8. Replace the path in the commands below with the file you changed.

**UTF-8 check (Windows PowerShell 5.1):**

```powershell
Get-Content src/agentharness/pytest_plugin.py -Encoding Byte -TotalCount 3
```

**UTF-8 check (PowerShell 7+ — `-Encoding Byte` was removed):**

```powershell
[System.IO.File]::ReadAllBytes("src/agentharness/pytest_plugin.py") | Select-Object -First 3
```

If the first two bytes are **255, 254** (hex `FF FE`, UTF-16 LE) or **254, 255** (hex `FE FF`, UTF-16 BE), the file is UTF-16. Convert before running pytest.

**Convert to UTF-8 (either PowerShell version):**

```powershell
$content = Get-Content src/agentharness/pytest_plugin.py -Raw
[System.IO.File]::WriteAllText(
    (Resolve-Path "src/agentharness/pytest_plugin.py"),
    $content,
    [System.Text.Encoding]::UTF8
)
```

### For External Contributors (once public)
See CONTRIBUTING.md. Short version: open an issue before writing code for large features. Small bug fixes: open a PR directly. All contributors sign a CLA (Apache CLA) to protect the project's ability to relicense if needed.

### What Makes a Good PR
- Has tests for the new behavior
- Has documentation (at minimum a docstring; ideally a docs/ entry)
- Is a single focused change (not "added three features and fixed four bugs")
- Updates CHANGELOG.md

---

## METRICS WE TRACK

### Adoption Health (weekly check)
- External teams in CI (verified via GitHub dependents or direct confirmation)
- PyPI downloads/week
- Open issues response time (target: under 48 hours for triage)
- CI pass rate (should be above 95%; if lower, something is flaky)
- Time-to-first-passing-test for new users

### Code Quality (per release)
- Test coverage: `pytest --cov` -- must be above 90% for core modules
- Type coverage: `mypy` -- must pass with strict mode on `src/agentharness/core/`
- Linting: `ruff` -- zero errors allowed

### User Satisfaction (per phase)
- Mean time to first working test (user interviews)
- Discord/GitHub issue sentiment
- % of design partners who renew past pilot

---

## DECISION LOG

> High-stakes decisions that were discussed and resolved. Brief record of what was decided and why, in case someone questions it later.

| Date | Decision | Decided By | Rationale Summary |
|---|---|---|---|
| April 2026 | `AssertionResult` + `REFS_*` on all harness assertions; `finish()` raises `AssertionError` | Core team | Structured outcomes for compliance reporters; regulatory cite list per assertion; pytest-compatible failures. AD-011. |
| April 2026 | Apache 2.0 license | Founder | Enterprise-friendly, patent protection, compatible with OSS dependencies. BSL and AGPL rejected. |
| April 2026 | Pytest as primary runner | Founder | Zero new tooling for CI. Engineers already know it. |
| April 2026 | OpenInference trace schema | Founder | Instant compatibility with Arize/LangFuse ecosystem. Apache 2.0. |
| April 2026 | Mock mode default | Founder | Safety non-negotiable. Accidental production writes would destroy community trust. |
| April 2026 | Start with LangGraph only (Phase 0) | Founder | Most production agents use LangGraph. Validate architecture before adding adapters. |
| April 2026 | Cassette sanitization default-on | Founder | Cassettes committed to VCS must not contain PII or secrets. Safe defaults prevent data leaks. |
| April 2026 | Context-local registry (not global) | Founder | Global registry breaks parallel pytest runs and multi-scenario concurrency. Context vars are safer. |
| April 2026 | Tiered emergency stop guarantees | Founder | Cannot guarantee sub-500ms stop for in-flight network calls. Honest tiered guarantees prevent overclaiming. |
| April 2026 | OpenAI Responses API as primary target | Founder | Assistants API deprecated Aug 2025, shutdown Aug 2026. Responses API is the future. |
| April 2026 | LangGraph `ToolNode.wrap_tool_call` / `awrap_tool_call` as primary intercept | Core team | Validated without patching LangGraph; AD-002 fallback (tool replacement) retained and tested. Evidence: `tests/unit/test_langgraph_intercept.py`. |

---

## LAUNCH CHECKLIST

> This checklist is for the Phase 1 public launch. Do not launch until all items are checked.

### Code Quality
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Coverage above 90% on core modules
- [ ] No open critical bugs
- [ ] mypy strict mode passes on `src/agentharness/core/`

### Documentation
- [ ] README has working 5-minute quickstart (tested by someone who didn't write it)
- [ ] All 3 launch examples work with `git clone && pip install && pytest`
- [ ] API reference is generated and deployed
- [ ] At least 2 guides in docs/guides/

### Distribution
- [ ] `pip install agentharness` works from PyPI
- [ ] Version 0.1.0 tagged in Git
- [ ] CHANGELOG.md has 0.1.0 entry
- [ ] GitHub release created with release notes

### Community
- [ ] Discord server created (or LangChain Discord channel requested)
- [ ] "Contributing" is easy: someone external submits a PR and it merges
- [ ] GOVERNANCE.md is published
- [ ] Roadmap is public (GitHub Projects or docs/)

### Launch Content
- [ ] HN Show HN post drafted and reviewed
- [ ] Blog post: "Why we built AgentHarness" published
- [ ] Social media thread ready to post same day as HN
- [ ] LangChain Discord post written

---

## FUTURE WORK (Not Yet Committed)

> Ideas that have been discussed but are not yet in the roadmap. Capture them here so they don't get lost.

- **Agent behavior fingerprinting**: generate a "behavioral signature" of an agent that can be diff'd against itself over time, without needing predefined golden traces
- **Automatic scenario generation**: given an agent definition, use an LLM to generate candidate test scenarios (adversarial, edge case, happy path)
- **Multi-tenant hosted cloud**: team collaboration, shared scenario libraries, cross-team regression dashboards
- **Real-time production monitoring adapter**: bridge between the test harness and production tracing -- production incidents automatically create test scenarios
- **Natural language scenario authoring**: "Test that the refund agent never refunds more than the original order amount" -- auto-generates YAML scenario
- **ISO/IEC 42001 full AI Management System template**: turnkey AI management system documentation generated from harness test results
- **Accessibility for web UI**: WCAG 2.1 AA compliance for Live Mode v2; documentation translations (EN/FR/DE minimum for EU audience)
- **Migration guides**: "Moving from LangSmith / AgentOps to AgentHarness" to onboard users with existing tooling

---

*project_context.md -- AgentHarness*
*This file is living documentation. Update it continuously; preserve superseded wording per **Document change policy** and [project_context_revisions.md](project_context_revisions.md). The best documentation is the documentation that's actually true.*
