"""Tests for ``agentharness run`` CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from agentharness.cli.main import cli
from agentharness.cli.run import run_command


def _argv(scenario: Path, *, mode: str = "mock") -> SimpleNamespace:
    """Minimal namespace matching argparse for :func:`run_command`."""
    return SimpleNamespace(scenario=str(scenario), mode=mode)


def test_cli_run_all_pass(tmp_path: Path) -> None:
    p = tmp_path / "ok.yaml"
    p.write_text(
        "tool_calls: [a, b]\n"
        "assertions:\n"
        "  - kind: called_before\n"
        "    earlier: a\n"
        "    later: b\n",
        encoding="utf-8",
    )
    code = run_command(_argv(p))
    assert code == 0


def test_cli_run_any_fail(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "tool_calls: [b, a]\n"
        "assertions:\n"
        "  - kind: called_before\n"
        "    earlier: a\n"
        "    later: b\n",
        encoding="utf-8",
    )
    code = run_command(_argv(p))
    assert code == 1


def test_cli_run_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    code = run_command(_argv(missing))
    assert code == 2


def test_cli_run_output_contains_summary_pass_and_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ok = tmp_path / "ok.yaml"
    ok.write_text(
        "tool_calls: [x]\nassertions: []\n",
        encoding="utf-8",
    )
    run_command(_argv(ok))
    out = capsys.readouterr().out
    assert "AgentHarness:" in out

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "tool_calls: [b, a]\n"
        "assertions:\n"
        "  - kind: called_before\n"
        "    earlier: a\n"
        "    later: b\n",
        encoding="utf-8",
    )
    run_command(_argv(bad))
    out2 = capsys.readouterr().out
    assert "AgentHarness:" in out2


def test_cli_entrypoint_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(
        "tool_calls: [a, b]\n"
        "assertions:\n"
        "  - kind: called_before\n"
        "    earlier: a\n"
        "    later: b\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["agentharness", "run", str(p)])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 0


def test_cli_default_mode_mock_no_extra_flags(tmp_path: Path) -> None:
    """Mock is default (AD-005); --mode is wired to trace ``harness.mode``."""
    p = tmp_path / "s.yaml"
    p.write_text("tool_calls: [a]\nassertions: []\n", encoding="utf-8")
    code_m = run_command(_argv(p, mode="mock"))
    code_l = run_command(_argv(p, mode="live"))
    assert code_m == 0 and code_l == 0
