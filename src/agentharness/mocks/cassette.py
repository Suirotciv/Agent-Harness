"""Cassette read/write — sanitized recordings of tool responses for deterministic replay.

Handles serialization, PII/secret scrubbing, and keyed lookup by tool name and normalized
argument hash (DOMAIN KNOWLEDGE / On Cassette Design; AD-005).

Import from :mod:`agentharness.mocks.cassette` directly — this module is **not** re-exported
from :mod:`agentharness.mocks` (see :mod:`agentharness.mocks.interceptor` for package exports).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REDACTED = "[REDACTED]"
_REDACTED_PII = "[REDACTED-PII]"


def _harness_version() -> str:
    try:
        from importlib.metadata import version

        return version("agentharness")
    except Exception:
        return "dev"


def utc_now_iso() -> str:
    """ISO 8601 UTC timestamp with Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def make_cassette_key(tool_name: str, args: dict[str, Any]) -> str:
    """Stable hash for tool name + arguments (KI-002).

    Uses ``sha256(tool_name + sorted_args_json)`` per DOMAIN KNOWLEDGE.
    """
    normalized = json.dumps(args, sort_keys=True, ensure_ascii=False)
    payload = tool_name + normalized
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Secret patterns — scrubbing cannot be disabled (AD-005).
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-.]+", re.IGNORECASE), _REDACTED),
    (re.compile(r"sk-[a-zA-Z0-9]{10,}"), _REDACTED),
    (re.compile(r"AKIA[0-9A-Z]{16}"), _REDACTED),
    (
        re.compile(
            r"(?i)(api[_-]?key|password|secret|token|authorization)\s*[:=]\s*"
            r"['\"]?([^\s\"'<>]{4,})"
        ),
        _REDACTED,
    ),
)

# PII patterns — optional scrubbing (default on).
_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+"
        ),
        _REDACTED_PII,
    ),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), _REDACTED_PII),
    (
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        _REDACTED_PII,
    ),
    (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), _REDACTED_PII),
)


def _scrub_string(s: str, *, scrub_secrets: bool, scrub_pii: bool) -> str:
    out = s
    if scrub_secrets:
        for pat, repl in _SECRET_PATTERNS:
            out = pat.sub(repl, out)
    if scrub_pii:
        for pat, repl in _PII_PATTERNS:
            out = pat.sub(repl, out)
    return out


def sanitize(
    value: Any,
    *,
    scrub_secrets: bool = True,
    scrub_pii: bool = True,
) -> Any:
    """Recursively redact secrets and/or PII in strings inside ``value``.

    Does not mutate the original. Secret scrubbing cannot be disabled (AD-005).
    """
    if not scrub_secrets:
        raise ValueError("Secret scrubbing cannot be disabled per AD-005")

    if isinstance(value, str):
        return _scrub_string(value, scrub_secrets=True, scrub_pii=scrub_pii)
    if isinstance(value, dict):
        return {
            sanitize(k, scrub_secrets=True, scrub_pii=scrub_pii): sanitize(
                v, scrub_secrets=True, scrub_pii=scrub_pii
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize(v, scrub_secrets=True, scrub_pii=scrub_pii) for v in value]
    if isinstance(value, tuple):
        return tuple(
            sanitize(v, scrub_secrets=True, scrub_pii=scrub_pii) for v in value
        )
    return copy.deepcopy(value)


def normalize_args(args: dict[str, Any]) -> dict[str, Any]:
    """JSON-round-trip with sorted keys for stable ``args_normalized``."""
    raw = json.dumps(args, sort_keys=True, ensure_ascii=False)
    out = json.loads(raw)
    if not isinstance(out, dict):
        msg = "normalized args must deserialize to a JSON object"
        raise TypeError(msg)
    return out


@dataclass
class CassetteEntry:
    """One recorded tool response keyed for lookup."""

    key: str
    tool_name: str
    args_normalized: dict[str, Any]
    response: Any
    recorded_at: str
    harness_version: str = field(default_factory=_harness_version)


@dataclass
class Cassette:
    """Sanitized cassette file payload (single JSON object on disk)."""

    scenario_id: str
    created_at: str
    mode: str
    entries: list[CassetteEntry]
    secrets_scrubbed: bool = True
    pii_scrubbed: bool = True

    def lookup(self, tool_name: str, args: dict[str, Any]) -> Any | None:
        """Return the recorded response for ``tool_name`` + normalized ``args``, or ``None``."""
        norm = normalize_args(args)
        key = make_cassette_key(tool_name, norm)
        for e in self.entries:
            if e.key == key:
                return e.response
        return None


def save(cassette: Cassette, path: str | Path) -> Path:
    """Write ``cassette`` as pretty-printed JSON (UTF-8, no BOM).

    Applies :func:`sanitize` to each entry's ``args_normalized`` and ``response``.
    ``secrets_scrubbed`` is always ``True`` in the written file. ``pii_scrubbed`` on
    the input cassette controls whether PII patterns are redacted (``True`` = scrub).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    scrub_pii = cassette.pii_scrubbed
    sanitized_entries: list[CassetteEntry] = []
    for e in cassette.entries:
        sanitized_entries.append(
            CassetteEntry(
                key=e.key,
                tool_name=e.tool_name,
                args_normalized=sanitize(
                    e.args_normalized, scrub_secrets=True, scrub_pii=scrub_pii
                ),
                response=sanitize(e.response, scrub_secrets=True, scrub_pii=scrub_pii),
                recorded_at=e.recorded_at,
                harness_version=e.harness_version,
            )
        )
    out = Cassette(
        scenario_id=cassette.scenario_id,
        created_at=cassette.created_at,
        mode=cassette.mode,
        entries=sanitized_entries,
        secrets_scrubbed=True,
        pii_scrubbed=cassette.pii_scrubbed,
    )
    payload = _cassette_to_json_dict(out)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    p.write_text(text, encoding="utf-8", newline="\n")
    return p.resolve()


def _cassette_to_json_dict(cassette: Cassette) -> dict[str, Any]:
    return {
        "scenario_id": cassette.scenario_id,
        "created_at": cassette.created_at,
        "mode": cassette.mode,
        "entries": [asdict(e) for e in cassette.entries],
        "secrets_scrubbed": cassette.secrets_scrubbed,
        "pii_scrubbed": cassette.pii_scrubbed,
    }


def _entry_from_dict(d: dict[str, Any]) -> CassetteEntry:
    return CassetteEntry(
        key=str(d["key"]),
        tool_name=str(d["tool_name"]),
        args_normalized=dict(d["args_normalized"])
        if isinstance(d["args_normalized"], dict)
        else {},
        response=d["response"],
        recorded_at=str(d["recorded_at"]),
        harness_version=str(d.get("harness_version", _harness_version())),
    )


def load(path: str | Path) -> Cassette:
    """Load a cassette JSON file."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "Cassette file must contain a JSON object"
        raise ValueError(msg)
    entries_raw = raw.get("entries", [])
    if not isinstance(entries_raw, list):
        msg = "Cassette 'entries' must be a list"
        raise ValueError(msg)
    entries = [_entry_from_dict(e) for e in entries_raw if isinstance(e, dict)]
    return Cassette(
        scenario_id=str(raw["scenario_id"]),
        created_at=str(raw["created_at"]),
        mode=str(raw["mode"]),
        entries=entries,
        secrets_scrubbed=bool(raw.get("secrets_scrubbed", True)),
        pii_scrubbed=bool(raw.get("pii_scrubbed", True)),
    )


def lookup(cassette: Cassette, tool_name: str, args: dict[str, Any]) -> Any | None:
    """Return the recorded response for ``tool_name`` + ``args``, or ``None``."""
    return cassette.lookup(tool_name, args)


def default_cassette_path(scenario_name: str, *, base_dir: Path | None = None) -> Path:
    """Return ``cassettes/{scenario_name}.json`` under ``base_dir`` or the cwd."""
    root = base_dir if base_dir is not None else Path.cwd()
    return (root / "cassettes" / f"{scenario_name}.json").resolve()


def verify_replay_determinism(
    scenario_path: str | Path,
    cassette_path: str | Path | None,
    *,
    runs: int = 10,
) -> bool:
    """Run ``scenario_path`` in replay mode ``runs`` times; return whether pass/fail matches each time.

    Compares :class:`~agentharness.assertions.base.AssertionResult` outcomes by
    ``(passed, assertion_name)`` per run. On mismatch, prints a short summary to stderr.
    """
    from agentharness.assertions.base import (
        AssertionResult,
        reset_results_collector,
        set_results_collector,
    )
    from agentharness.cli.run import _run_yaml_assertions
    from agentharness.core.runner import run_scenario

    path = Path(scenario_path)
    if not path.is_file():
        msg = f"scenario not found: {path}"
        raise FileNotFoundError(msg)

    import yaml

    raw = path.read_text(encoding="utf-8")
    loaded = yaml.safe_load(raw)
    data: dict[str, Any] = loaded if isinstance(loaded, dict) else {}

    resolved: Path = (
        Path(cassette_path).resolve()
        if cassette_path is not None
        else default_cassette_path(path.stem)
    )

    signatures: list[list[tuple[bool, str]]] = []
    for _ in range(runs):
        collected: list[AssertionResult] = []
        tok = set_results_collector(collected)
        try:
            result = run_scenario(path, mode="replay", cassette_path=resolved)
            try:
                _run_yaml_assertions(data, result.trace)
            except AssertionError:
                pass
        finally:
            reset_results_collector(tok)

        signatures.append([(r.passed, r.assertion_name) for r in collected])

    first = signatures[0]
    diverged = [i for i, sig in enumerate(signatures[1:], start=2) if sig != first]
    if diverged:
        sys.stderr.write(
            "Replay determinism check failed: runs "
            f"{', '.join(str(n) for n in diverged)} "
            f"differ from run 1 (first run: {len(first)} assertion outcomes).\n",
        )
        return False
    return True
