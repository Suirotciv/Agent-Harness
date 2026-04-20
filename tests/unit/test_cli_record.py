"""Tests for ``agentharness record`` CLI."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agentharness.cli.record import record_command
from agentharness.mocks.cassette import load


def _argv(
    scenario: Path,
    *,
    mode: str = "mock",
    output: str | None = None,
    allow_sensitive_recording: bool = False,
    allow_real_tools: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        scenario=str(scenario),
        mode=mode,
        output=output,
        allow_sensitive_recording=allow_sensitive_recording,
        allow_real_tools=allow_real_tools,
    )


def test_record_mock_default_path_valid_cassette(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "case.yaml"
    p.write_text(
        "tool_calls: [a, b]\n"
        "assertions:\n"
        "  - kind: called_before\n"
        "    earlier: a\n"
        "    later: b\n",
        encoding="utf-8",
    )
    code = record_command(_argv(p, mode="mock"))
    assert code == 0
    out = capsys.readouterr().out
    expected = tmp_path / "cassettes" / "case.json"
    assert expected.is_file()
    assert "Cassette saved to" in out and "(2 entries)" in out

    c = load(expected)
    assert c.scenario_id == p.as_posix()
    assert len(c.entries) == 2


def test_record_custom_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(
        "tool_calls: [x]\n"
        "assertions: []\n",
        encoding="utf-8",
    )
    dest = tmp_path / "my" / "tape.json"
    code = record_command(_argv(p, mode="mock", output=str(dest)))
    assert code == 0
    assert dest.is_file()
    assert "Cassette saved to" in capsys.readouterr().out


def test_record_live_without_allow_real_tools_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "s.yaml"
    p.write_text("tool_calls: [a]\nassertions: []\n", encoding="utf-8")
    code = record_command(_argv(p, mode="live", allow_real_tools=False))
    assert code == 2
    err = capsys.readouterr().err
    assert "Live mode requires --allow-real-tools" in err


def test_record_allow_sensitive_sets_pii_scrubbed_false(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "s.yaml"
    p.write_text("tool_calls: [a]\nassertions: []\n", encoding="utf-8")
    out_file = tmp_path / "c.json"
    code = record_command(
        _argv(
            p,
            mode="mock",
            output=str(out_file),
            allow_sensitive_recording=True,
        ),
    )
    assert code == 0
    assert "PII scrubbing is disabled" in capsys.readouterr().err
    c = load(out_file)
    assert c.pii_scrubbed is False


def test_record_missing_scenario_exits_2(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    code = record_command(_argv(missing, mode="mock"))
    assert code == 2
