"""Tests for :mod:`agentharness.mocks.cassette`."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from agentharness.mocks.cassette import (
    Cassette,
    CassetteEntry,
    default_cassette_path,
    load,
    lookup,
    make_cassette_key,
    sanitize,
    save,
    utc_now_iso,
)


def test_make_cassette_key_order_independent() -> None:
    a = {"z": 1, "a": 2, "m": 3}
    b = {"m": 3, "a": 2, "z": 1}
    assert make_cassette_key("tool_x", a) == make_cassette_key("tool_x", b)


def test_sanitize_redacts_secret_pattern() -> None:
    s = "prefix sk-abcdefghijklmnopqrstuvwxyz0123456789 suffix"
    out = sanitize(s)
    assert "sk-" not in out
    assert "[REDACTED]" in out


def test_sanitize_redacts_email_pii() -> None:
    s = "contact user@example.com please"
    out = sanitize(s, scrub_pii=True)
    assert "user@example.com" not in out
    assert "[REDACTED-PII]" in out


def test_sanitize_rejects_disabled_secrets() -> None:
    with pytest.raises(ValueError, match="Secret scrubbing cannot be disabled"):
        sanitize("x", scrub_secrets=False)


def test_sanitize_no_mutation() -> None:
    nested: dict = {"a": 1, "b": {"token": "sk-123456789012345678901234567890"}}
    original = {"outer": nested}
    snapshot = copy.deepcopy(original)
    sanitize(original)
    assert original == snapshot


def test_save_load_round_trip(tmp_path: Path) -> None:
    ts = utc_now_iso()
    c = Cassette(
        scenario_id="scn/one",
        created_at=ts,
        mode="record",
        entries=[
            CassetteEntry(
                key=make_cassette_key("t", {"x": 1}),
                tool_name="t",
                args_normalized={"x": 1},
                response={"ok": True},
                recorded_at=ts,
                harness_version="0.0.1",
            ),
        ],
        secrets_scrubbed=True,
        pii_scrubbed=True,
    )
    path = tmp_path / "c.json"
    save(c, path)
    loaded = load(path)
    assert loaded.scenario_id == c.scenario_id
    assert loaded.mode == "record"
    assert len(loaded.entries) == 1
    assert loaded.entries[0].response == {"ok": True}


def test_load_entry_count(tmp_path: Path) -> None:
    ts = utc_now_iso()
    c = Cassette(
        scenario_id="s",
        created_at=ts,
        mode="record",
        entries=[
            CassetteEntry(
                key=make_cassette_key("a", {}),
                tool_name="a",
                args_normalized={},
                response=1,
                recorded_at=ts,
            ),
            CassetteEntry(
                key=make_cassette_key("b", {"q": 1}),
                tool_name="b",
                args_normalized={"q": 1},
                response=2,
                recorded_at=ts,
            ),
        ],
    )
    p = tmp_path / "x.json"
    save(c, p)
    assert len(load(p).entries) == 2


def test_lookup_hit_and_miss() -> None:
    ts = utc_now_iso()
    args = {"order": "42"}
    key = make_cassette_key("lookup_order", args)
    c = Cassette(
        scenario_id="s",
        created_at=ts,
        mode="record",
        entries=[
            CassetteEntry(
                key=key,
                tool_name="lookup_order",
                args_normalized={"order": "42"},
                response={"found": True},
                recorded_at=ts,
            ),
        ],
    )
    assert lookup(c, "lookup_order", args) == {"found": True}
    assert lookup(c, "lookup_order", {"order": "99"}) is None


def test_secrets_scrubbed_true_after_save(tmp_path: Path) -> None:
    ts = utc_now_iso()
    c = Cassette(
        scenario_id="s",
        created_at=ts,
        mode="record",
        entries=[],
        secrets_scrubbed=False,
        pii_scrubbed=True,
    )
    p = tmp_path / "y.json"
    save(c, p)
    loaded = load(p)
    assert loaded.secrets_scrubbed is True


def test_default_cassette_path(tmp_path: Path) -> None:
    p = default_cassette_path("refund_happy", base_dir=tmp_path)
    assert p == tmp_path / "cassettes" / "refund_happy.json"
