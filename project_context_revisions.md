# project_context_revisions.md

Archive of substantive **`PROJECT_CONTEXT.md`** edits (newest first). When an inline change would be unreadable, full prior text lands here per document change policy.

---

## 2026-04-20 — PyPI 0.1.0a2 (documentation release)

**Added / updated in `PROJECT_CONTEXT.md`:** `CURRENT STATUS` line `Last Release: 0.1.0a2 (alpha)`; Checkpoint 1 exit criterion bullet updated from `pip install agentharness==0.1.0a1` to `pip install pytest-agentharness==0.1.0a2` (correct distribution name).

**What shipped:** `pyproject.toml` / `__version__` **0.1.0a2**; `CHANGELOG.md` `[0.1.0a2]`; README and `docs/demo.md` install pins; no runtime API changes.

---

## 2026-04-19 — PyPI 0.1.0a1 alpha prep (build + release workflow)

**Added / updated in `PROJECT_CONTEXT.md`:** CURRENT STATUS line `Last Release: 0.1.0a1 (alpha)`; Checkpoint 1 sprint row **PyPI 0.1.0-alpha prep** **DONE**; `CHANGELOG.md` section `[0.1.0a1]`.

**What shipped:** `pyproject.toml` `version = "0.1.0a1"`, setuptools build backend + package discovery, `license = { text = "Apache-2.0" }`, keywords/classifiers/`Issues` URL; `src/agentharness/__init__.py` `__version__`; `src/agentharness/py.typed`; `.github/workflows/release.yml` (tags `v*.*.*` / `v*.*.*a*`, `twine upload` via `PYPI_API_TOKEN`).

---

## 2026-04-19 — Replay mode (interceptor, runner, CLI)

**Added / updated in `PROJECT_CONTEXT.md`:** KEY FILE LOCATIONS: `interceptor.py` REPLAY + `core/runner.py` `cassette_path=`; Checkpoint 1 sprint row **Replay mode** **DONE**; `CHANGELOG.md` [Unreleased].

**What shipped:** `InterceptMode.REPLAY`, `ReplayCassetteError`, `HarnessInterceptor(..., cassette=)`; `run_scenario(..., mode="replay", cassette_path=)`; `verify_replay_determinism()`; `agentharness run --replay`; tests `tests/unit/test_replay.py`.

---

## 2026-04-19 — PROJECT_CONTEXT sprint tables (owner labels)

Owner labels normalized to Founder throughout sprint tables; artifact scan clean.

---

## 2026-04-19 — cli/record.py (`agentharness record`)

**Added / updated in `PROJECT_CONTEXT.md`:** KEY FILE LOCATIONS line for `src/agentharness/cli/record.py`; Checkpoint 1 sprint row **cli/record.py** **DONE**; `CHANGELOG.md` [Unreleased].

**What shipped:** `record_command` (`--output`, `--mode` live/mock, `--allow-real-tools`, `--allow-sensitive-recording`); `core/runner.py` optional `mode` override; `RunResult.tool_call_records`; `tests/unit/test_cli_record.py`.

---

## 2026-04-19 — mocks/cassette.py (KI-002, KI-006)

**Added / updated in PROJECT_CONTEXT.md:** KEY FILE LOCATIONS line for src/agentharness/mocks/cassette.py; KI-002 and KI-006 **RESOLVED** with evidence; Checkpoint 1 sprint row **mocks/cassette.py** **DONE**; exit criterion bullet for KI-002/KI-006 references cassette helpers.

**What shipped:** Cassette, CassetteEntry, make_cassette_key, sanitize, save/load/lookup, default_cassette_path; `tests/unit/test_cassette.py`; `CHANGELOG.md` [Unreleased].

---

## 2026-04-19 — Telemetry `TraceCollector` (Phase 1 Checkpoint 1)

**Added / updated in `PROJECT_CONTEXT.md`:** Checkpoint 1 sprint rows **telemetry/collector.py** and **Update example 01 to use collector** marked **DONE**; KEY FILE LOCATIONS entry for `src/agentharness/telemetry/collector.py` (import from `agentharness.telemetry.collector`, not package root).

**What shipped:** `TraceCollector` records `ToolCallRecord` rows as OpenInference-aligned TOOL spans; `core/runner.py` and `examples/01_customer_support_langgraph/support/executor.py` wrap `HarnessInterceptor.record_call` to feed the collector; `support/trace_builder.py` stubbed; `tests/unit/test_collector.py`; `telemetry/__init__.py` documents direct import (with `jsonl`). `CHANGELOG.md` [Unreleased]; Ruff `extend-exclude` lists `assertions` and `adapters` only so `telemetry/` is linted.

---

## 2026-04-19 — `.gitattributes` + LF renormalization

**Added / updated in `PROJECT_CONTEXT.md`:** Sprint table row **.gitattributes + LF normalization** (first row, **DONE**): notes repo-wide LF via `.gitattributes`, `git add --renormalize .`, Windows CRLF warning mitigation; marked as infrastructure add-on before collector work.

**What shipped:** `.gitattributes` at repo root; `git add --renormalize .` applied; `CHANGELOG.md` updated.

---

## 2026-04-19 — Phase 1 Checkpoint 1: `.editorconfig`, Ruff, CI lint

**Added / updated in `PROJECT_CONTEXT.md`:** Sprint table row **.editorconfig + ruff in CI** marked **DONE** (notes: `.editorconfig`, `ruff` in `[dev]`, tool config, parallel `lint` job, exclusions).

**What shipped:** Root `.editorconfig`; `pyproject.toml` — `ruff>=0.4.0`, `[tool.ruff]` (line-length 88, `extend-exclude` for assertions/adapters/telemetry), `[tool.ruff.lint]` (E/F/W/I, ignore `E501`), `[tool.ruff.format]`; Ruff auto-fix + format on allowed `src/` paths; `.github/workflows/ci.yml` — new `lint` job (Python 3.12, `pip install -e ".[dev]"`, `ruff check` / `ruff format --check`).

---

## 2026-04-19 — Phase 1 Checkpoint 1: sprint plan + status

**Added / updated in `PROJECT_CONTEXT.md`:** **CURRENT STATUS** set to Phase 1 MVP, Checkpoint 1 of 3, no blockers, Last Updated April 2026 (week/start/target lines removed). **What We Are Building Right Now:** struck “Next: telemetry collector wiring…”; replaced with Phase 1 Checkpoint 1 priorities (collector, cassette pipeline, regression diff, 0.1.0-alpha). New **PHASE 1 SPRINT PLAN** after **PHASE 1 BACKLOG**: Checkpoint 1 table (`.editorconfig`/ruff, `telemetry/collector.py`, `mocks/cassette.py`, `cli/record.py`, replay mode, `reporting/diff.py`, example 01, PyPI alpha), exit criteria, and stub for Checkpoints 2–3. **PHASE 1 BACKLOG:** items 1–3 struck with **Checkpoint 1** notes.

---

## 2026-04-19 — UTF-16 warning list: `README.md` + `CHANGELOG.md`

**Added / updated in `PROJECT_CONTEXT.md`:** Under **CONTRIBUTION PROCESS → Windows: UTF-8 for `.py` files**, the list of files affected by UTF-16 save issues now includes `README.md` and `CHANGELOG.md` (confirmed on this machine during Phase 0 close-out: `__main__.py` + README/CHANGELOG edits). Added a short note that repo Markdown is not exempt and that the same UTF-16 LE pattern and UTF-8 re-save fix apply.

---

## 2026-04-19 — Phase 0 exit review (complete)

**Added / updated in `PROJECT_CONTEXT.md`:** Sprint 2 row “Phase 0 exit review” marked **DONE**; CURRENT STATUS set to Phase 0 complete / Sprint 2 closed; KI-001 and KI-005 remain RESOLVED with evidence.

**What was verified:** Sprint 1 exit (pytest + `assert_called_before` + `@scenario`/`run`); `examples/01_customer_support_langgraph/` (5/5), full `tests/unit/` (67/67), `agentharness run scenarios/safety/refund_limit_guard.yaml` (pass/fail summary), CI matrix (3.10–3.12, editable install, unit pytest), AD-002 fallback + `test_langgraph_intercept.py`, README roadmap text-only (no `Founder_Docs/` link), regression slices for structural/argument/safety/resource/trace/console/cli/plugin/intercept tests, `mypy` clean on listed packages after fixing `Span.status_code` default in `core/trace.py` (literal `"UNSET"`).

---

## 2026-04-19 — Root README + Sprint 2 README task

**Added / updated in `PROJECT_CONTEXT.md`:** Sprint 2 row “README first draft” marked **DONE** (summary of root README contents).

**What shipped:** Repository root `README.md` (install commands aligned with `pyproject.toml`, quickstart via `examples/01_customer_support_langgraph/`, assertion table from `REFS_*`, CLI usage, roadmap link to `Founder_Docs/project_proposal.md`).

---

## 2026-04-19 — Phase 0 example 01 (customer support LangGraph)

**Added / updated in `PROJECT_CONTEXT.md`:** Sprint 2 row "Example 01: Customer support refund agent" marked **DONE**; KEY FILE LOCATIONS line for `examples/01_customer_support_langgraph/` expanded (5 scenarios, executor); `agentharness run` CLI row note updated (`set_results_collector` instead of per-module `finish` patching).

**What shipped:** `examples/01_customer_support_langgraph/` with mock LangGraph tool execution, YAML `steps`, five scenario files, `test_refund_agent.py`, and README.

---

## 2026-04-19 — KI-007 / AD-011 — `finish()` result collection (CLI vs pytest)

**Added / updated in `PROJECT_CONTEXT.md`:** AD-011 extended with `_results_collector` `ContextVar` and `set_results_collector` / `reset_results_collector`; new KI-007 row **RESOLVED** (prior risk: `cli/run.py` patched `finish` per imported module, violating single `finish()` path and missing `argument` / `safety` / `resource` assertions).

**What shipped:** `assertions/base.py` appends to the optional collector inside `finish()` before raising; `cli/run.py` binds a list for `agentharness run`; `pytest_plugin.py` documents that pytest continues to use stash + `LOGREPORT_PENDING` without requiring the ContextVar.

---
