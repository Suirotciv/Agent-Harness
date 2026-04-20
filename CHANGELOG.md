# Changelog

All notable changes to AgentHarness will be documented in this file.

## [0.1.0a1] -- 2026-04-19

### Summary

First alpha release. Checkpoint 1 complete: record, replay,
regression diff, and pytest-native behavioral assertions
for LangGraph agents. Not yet recommended for production use.

### Included

### Added
- `src/agentharness/reporting/diff.py`: `TraceDiff`, `SpanDiff`,
  `diff_traces` (strict/subset/superset modes), `format_diff`
  (Rich with plain fallback); `agentharness run --diff PATH`
  and `--diff-mode` flag on the run subcommand; baseline loaded
  from cassette `.json` or trace `.jsonl`. Tests:
  `tests/unit/test_diff.py`.

- Replay: `HarnessInterceptor` REPLAY mode + `ReplayCassetteError`; `run_scenario(..., cassette_path=)`; `agentharness run --replay`; `verify_replay_determinism()` in `mocks/cassette.py`. Tests: `tests/unit/test_replay.py`.

- `src/agentharness/cli/record.py`: `agentharness record` writes a sanitized cassette from `run_scenario` tool-call records; `--output` / default `cassettes/<stem>.json`; `--mode live` requires `--allow-real-tools` (AD-005); `--allow-sensitive-recording` (PII off). `core/runner.py` optional `mode` override; `RunResult.tool_call_records`. Tests: `tests/unit/test_cli_record.py`.

- src/agentharness/mocks/cassette.py: Cassette / CassetteEntry, make_cassette_key (KI-002), sanitize and save/load/lookup (KI-006, AD-005), default_cassette_path; `tests/unit/test_cassette.py`.

- `src/agentharness/telemetry/collector.py`: `TraceCollector` (ToolCallRecord → OpenInference TOOL spans with tool.name, input.value, output.value); `core/runner.py` and `examples/01_customer_support_langgraph/support/executor.py` wrap `HarnessInterceptor.record_call` to feed the collector; `support/trace_builder.py` stubbed; `tests/unit/test_collector.py`. Ruff `extend-exclude` narrowed to `assertions` and `adapters` only so `telemetry/` is linted.

- Root `.gitattributes` (`* text=auto eol=lf`, per-extension rules, binary globs); `git add --renormalize .` to apply LF to tracked files and reduce CRLF/LF churn on Windows.
- Root `.editorconfig` (UTF-8, LF, trim; `*.md` has `trim_trailing_whitespace = false`); `ruff>=0.4.0` in `[dev]`; `[tool.ruff]` / `[tool.ruff.lint]` (E/F/W/I; `E501` ignored until docstring line wrap) / `[tool.ruff.format]`; `extend-exclude` for `assertions` / `adapters` until those packages are reformatted on schedule. CI: parallel `lint` job (Python 3.12, `pip install -e ".[dev]"`, `python -m ruff check src/`, `python -m ruff format --check src/`).
- `agentharness/__main__.py` and `agentharness/cli/__main__.py`: run the CLI via `python -m agentharness …` or `python -m agentharness.cli …` (same `cli()` entry as the `agentharness` console script).

### Changed
- `PROJECT_CONTEXT.md`: Phase 1 MVP status (Checkpoint 1 of 3); **PHASE 1 SPRINT PLAN** with Checkpoint 1 (record/replay/diff, PyPI 0.1.0-alpha prep); PHASE 1 BACKLOG items 1–3 struck with **Checkpoint 1**; “What We Are Building Right Now” updated for Checkpoint 1 priorities.
- **Phase 0 complete** — foundation, pytest plugin, assertions, LangGraph adapter + fallback tests, trace JSONL, console reporter, `agentharness run` CLI, LangGraph refund example, root README, CI on Python 3.10–3.12.

### Fixed
- `core/trace.py`: `Span.status_code` default is the literal `"UNSET"` so strict mypy accepts it as `SpanStatusCode` (was assigning `telemetry.schema.STATUS_UNSET`, inferred as plain `str`).

### Added
- Root `README.md`: project overview, install, quickstart (example scenario + pytest), “what it is not,” assertion reference table, CLI, roadmap (text only; no `Founder_Docs/` link), license/contributing pointers.
- Example `examples/01_customer_support_langgraph/`: mock LangGraph refund tool suite (`support/refund_tools.py`), YAML ``steps`` executor with `HarnessInterceptor` + `create_intercepted_tool_node` (`support/executor.py`, `support/trace_builder.py`), five scenarios, `test_refund_agent.py`, README; local `run` fixture for the example package.
- `agentharness run` CLI (`cli/main.py` top-level group with argparse; `run` loads YAML + `run_scenario()`, sets `harness.mode` from ``--mode`` mock/live, optional YAML ``assertions`` via ``set_results_collector`` / ``finish()`` + `ConsoleReporter`). Stubs: `watch`, `record`, `report`. Scenario `scenarios/safety/refund_limit_guard.yaml` for Phase 0 exit criterion. Tests: `tests/unit/test_cli_run.py`.
- Console reporter `reporting/console.py` (`ConsoleReporter`, Rich panels with ASCII fallback); `reporting/__init__.py` documents submodule imports only (no re-exports). Pytest plugin: autouse item binding, `LOGREPORT_PENDING` flushing in `pytest_runtest_makereport` (correlates with test pass/fail so expected assertion failures inside `pytest.raises` do not spam the summary), `pytest_runtest_logreport` stub, `pytest_terminal_summary` output; `finish()` in `base.py` records results before raising. Tests: `tests/unit/test_console_reporter.py`.
- `AssertionResult` dataclass and `finish()` in `assertions/base.py`: every harness assertion returns a structured result with human-readable `message`, `regulatory_refs` (compliance mapping via `REFS_*` constants: EU AI Act articles, NIST AI RMF TEVV, Colorado SB 24-205, OWASP LLM Top 10 citations), and `details` (tool names, constraints, observed sequences/values) for future reporters and evidence export. Exported from `agentharness` and `agentharness.assertions`.
- Trace JSONL serialization in `telemetry/jsonl.py` (AD-008 paths under `.agentharness/traces/`); `telemetry/__init__.py` does not re-export (circular import with `core.trace`); tests `tests/unit/test_trace_jsonl.py`
- Argument assertions `assert_arg_lte`, `assert_arg_pattern`, `assert_arg_schema`, `assert_arg_not_contains` in `assertions/argument.py`; safety `assert_approval_gate`, `assert_no_loop` in `assertions/safety.py`; resource `assert_cost_under` in `assertions/resource.py` (optional `tokencost`); unit tests `test_argument_assertions.py`, `test_safety_assertions.py`, `test_resource_assertions.py`; optional extra `[resource]`; `tokencost` and `types-jsonschema` in `[dev]`
- Structural assertions `assert_call_count`, `assert_completion`, `assert_mutual_exclusion` in `assertions/structural.py`; unit tests `tests/unit/test_structural_batch.py`; exported from package root
- Sprint 1 exit criteria evidence: `tests/unit/test_sprint1_exit_criteria.py`, `scenarios/refund_happy_path.yaml`; `run_scenario()` loads optional `tool_calls` from YAML and emits synthetic TOOL spans (Phase 0); dependency `pyyaml`; dev typing `types-PyYAML`
- GitHub Actions workflow `.github/workflows/ci.yml`: unit tests on pull requests and pushes to `main`/`master`, Python 3.10 / 3.11 / 3.12 matrix, `pytest tests/unit/`
- Pytest plugin (`agentharness.pytest_plugin`): `run` fixture and `agentharness_scenario` marker; `@scenario` in `scenario.py`; `RunResult` + `run_scenario()` in `core/result.py` and `core/runner.py` (Phase 0 shell: trace with `harness.scenario_id`). `pytest11` entry point targets `agentharness.pytest_plugin`. Tests in `tests/unit/test_pytest_plugin.py`; `tests/conftest.py` sets `pytest_plugins = ["pytester"]` for plugin tests
- `assert_called_before` in `assertions/structural.py` (ordering over `Trace` tool spans, `ToolCallRecord` sequences, or ordered tool name lists); unit tests in `tests/unit/test_assert_called_before.py`; re-exported from package root
- `Trace` and `Span` Pydantic models in `core/trace.py` (OTLP-style ids, nanosecond timestamps, `extra="allow"`) plus `telemetry/schema.py` canonical attribute keys (`harness.*`, `gen_ai.*`, OpenInference tool/LLM fields)
- Unit tests `tests/unit/test_trace_models.py` for trace/span validation and JSON round-trip
- Project scaffolding: full directory structure, placeholder files, pyproject.toml, Apache 2.0 license, .gitignore
- `HarnessInterceptor` in `mocks/interceptor.py`: framework-agnostic tool call recording and mock response routing (sync and async)
- `ToolCallRecord` dataclass for capturing tool call name, args, response, timing, and mock status
- `MockNotConfiguredError` for loud failure when tools are called in mock mode without a registered response
- `InterceptMode` enum (MOCK / LIVE)
- LangGraph adapter in `adapters/langgraph.py` with two interception strategies:
  - Native wrapper (primary): uses ToolNode's `wrap_tool_call` / `awrap_tool_call` API
  - Tool replacement (fallback, AD-002): replaces tool callables before ToolNode construction
- 8 validation tests in `tests/unit/test_langgraph_intercept.py` confirming both interception strategies work (sync, async, mock, live, multi-tool)
- Validated against `langgraph-prebuilt 1.0.10`, `langchain-core 1.3.0`

### Fixed
- `assertions/base.py` (KI-007): replaced unsafe per-module `finish` patching in the CLI with a `ContextVar` collector (`set_results_collector` / `reset_results_collector`) so all assertion modules record through one `finish()` implementation (AD-011).
- `pytest_plugin.py`: read configuration failures from `CallInfo.excinfo` (pytest versions where `TestReport` has no `excinfo` attribute).
- Fixed UTF-16 encoding on all project files (Windows Write tool artifact); all source files are now UTF-8
- Fixed PEP 440 version string (`0.0.1.dev0` instead of `0.0.1-dev`)

### Changed
- All public assertion helpers in `assertions/structural.py`, `argument.py`, `safety.py`, and `resource.py` now return `AssertionResult` (signatures unchanged except return type). Failures go through `finish()` → `AssertionError(result.message)` for pytest; invalid inputs still use `ValueError` where applicable. See AD-011 in `PROJECT_CONTEXT.md`.
- `pyproject.toml`: `[dev]` includes `agentharness[resource]` so `tokencost` is pinned only under `[resource]` (no duplicate pin); `[all]` drops redundant `resource` (still pulled via `dev`); comment documents mypy stubs + CI install line
- `project_context.md`: KI-001 and KI-005 marked RESOLVED; AD-002 expanded with LangGraph native `wrap_tool_call` discovery; Sprint 1 task table updated; DOMAIN KNOWLEDGE section documents runtime config and ToolNode return shape
- `project_context.md`: Sprint 1 exit criteria **Evidence** paragraph (test + YAML + synthetic spans); AD-011 (`AssertionResult` / compliance assertion returns); CONTRIBUTION PROCESS UTF-8 file list extended for assertion unit tests saved as UTF-16 on Windows
- `pyproject.toml`: optional `[dev]` extra with `pytest-asyncio` and `types-PyYAML`; `[all]` includes `dev`; runtime dependency `pyyaml`


## [Unreleased]

- pyproject.toml URLs corrected to https://github.com/Suirotciv/AGENTHARNESS; dist/ and *.egg-info/ added to .gitignore.

