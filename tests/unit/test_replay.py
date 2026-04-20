"""Tests for replay mode (interceptor, runner, CLI, determinism helper)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from agentharness.cli.run import run_command
from agentharness.core.runner import run_scenario
from agentharness.mocks.cassette import (
    Cassette,
    CassetteEntry,
    default_cassette_path,
    make_cassette_key,
    normalize_args,
    save,
    utc_now_iso,
    verify_replay_determinism,
)
from agentharness.mocks.interceptor import (
    HarnessInterceptor,
    InterceptMode,
    ReplayCassetteError,
)


def _cassette_with_tools(
    path: Path,
    pairs: list[tuple[str, Any]],
    *,
    scenario_id: str = "s",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = utc_now_iso()
    entries: list[CassetteEntry] = []
    for tool_name, response in pairs:
        args_norm = normalize_args({})
        entries.append(
            CassetteEntry(
                key=make_cassette_key(tool_name, args_norm),
                tool_name=tool_name,
                args_normalized=args_norm,
                response=response,
                recorded_at=ts,
            ),
        )
    c = Cassette(
        scenario_id=scenario_id,
        created_at=ts,
        mode="record",
        entries=entries,
    )
    save(c, path)
    return path.resolve()


def test_interceptor_replay_returns_cassette_response(tmp_path: Path) -> None:
    cp = _cassette_with_tools(
        tmp_path / "cassettes" / "x.json",
        [("t1", {"ok": True})],
    )
    from agentharness.mocks.cassette import load

    cassette = load(cp)
    hi = HarnessInterceptor(
        mode=InterceptMode.REPLAY,
        cassette=cassette,
    )
    out = hi.intercept_sync("t1", {}, "id-1")
    assert out == {"ok": True}
    assert hi.calls[0].response == {"ok": True}


def test_interceptor_replay_raises_when_missing_entry() -> None:
    from agentharness.mocks.cassette import Cassette

    cassette = Cassette(
        scenario_id="x",
        created_at=utc_now_iso(),
        mode="record",
        entries=[],
    )
    hi = HarnessInterceptor(mode=InterceptMode.REPLAY, cassette=cassette)
    with pytest.raises(ReplayCassetteError):
        hi.intercept_sync("unknown", {}, "id")


def test_run_scenario_replay_uses_cassette(tmp_path: Path) -> None:
    scen = tmp_path / "case.yaml"
    scen.write_text(
        "tool_calls: [a, b]\n"
        "assertions:\n"
        "  - kind: called_before\n"
        "    earlier: a\n"
        "    later: b\n",
        encoding="utf-8",
    )
    cp = _cassette_with_tools(
        tmp_path / "cass.json",
        [("a", "A"), ("b", "B")],
    )
    r = run_scenario(scen, mode="replay", cassette_path=cp)
    names = [c.tool_name for c in r.tool_call_records]
    assert names == ["a", "b"]
    assert r.tool_call_records[0].response == "A"
    assert r.tool_call_records[1].response == "B"


def test_run_scenario_replay_default_cassette_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    scen = tmp_path / "myscenario.yaml"
    scen.write_text("tool_calls: [x]\nassertions: []\n", encoding="utf-8")
    expected = default_cassette_path("myscenario")
    _cassette_with_tools(expected, [("x", 42)])
    r = run_scenario(scen, mode="replay", cassette_path=None)
    assert r.tool_call_records[0].response == 42


def test_verify_replay_determinism_all_agree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    scen = tmp_path / "d.yaml"
    scen.write_text(
        "tool_calls: [a, b]\n"
        "assertions:\n"
        "  - kind: called_before\n"
        "    earlier: a\n"
        "    later: b\n",
        encoding="utf-8",
    )
    _cassette_with_tools(default_cassette_path("d"), [("a", 1), ("b", 2)])
    assert verify_replay_determinism(scen, None, runs=5) is True


def test_cli_replay_forces_replay_mode(tmp_path: Path) -> None:
    scen = tmp_path / "c.yaml"
    scen.write_text("tool_calls: [u]\nassertions: []\n", encoding="utf-8")
    _cassette_with_tools(tmp_path / "cass.json", [("u", 9)])
    args = SimpleNamespace(
        scenario=str(scen),
        mode="live",
        replay=str(tmp_path / "cass.json"),
    )
    code = run_command(args)
    assert code == 0


def test_cli_replay_missing_cassette_exit_2(tmp_path: Path) -> None:
    scen = tmp_path / "m.yaml"
    scen.write_text("tool_calls: [z]\nassertions: []\n", encoding="utf-8")
    args = SimpleNamespace(
        scenario=str(scen),
        mode="mock",
        replay=str(tmp_path / "nope.json"),
    )
    assert run_command(args) == 2


def test_cli_replay_warns_mode_ignored(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scen = tmp_path / "w.yaml"
    scen.write_text("tool_calls: [u]\nassertions: []\n", encoding="utf-8")
    _cassette_with_tools(tmp_path / "cass.json", [("u", 1)])
    monkeypatch.setattr(
        sys,
        "argv",
        ["agentharness", "run", str(scen), "--replay", str(tmp_path / "cass.json"), "--mode", "mock"],
    )
    args = SimpleNamespace(
        scenario=str(scen),
        mode="mock",
        replay=str(tmp_path / "cass.json"),
    )
    assert run_command(args) == 0
    err = capsys.readouterr().err
    assert "WARNING: --mode is ignored" in err
