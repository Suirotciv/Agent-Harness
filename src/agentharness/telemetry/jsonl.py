"""Trace JSONL serialization (AD-008).

One trace per file by default: a single NDJSON line containing the full :class:`~agentharness.core.trace.Trace`
as JSON (Pydantic ``model_dump(mode='json')``). Files may be appended with additional lines for multiple
traces in one file.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentharness.core.trace import Trace


def trace_to_jsonl_line(trace: Trace) -> str:
    """Serialize ``trace`` to one compact JSON line (no embedded newlines)."""
    payload: dict[str, Any] = trace.model_dump(mode="json")
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def parse_trace_jsonl_line(line: str) -> Trace:
    """Parse a single JSON line back into a :class:`Trace`."""
    data = json.loads(line)
    return Trace.model_validate(data)


def write_trace_jsonl(
    path: str | Path,
    trace: Trace,
    *,
    append: bool = False,
) -> Path:
    """Write one trace as a single line to ``path`` (UTF-8). Creates parent dirs."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = trace_to_jsonl_line(trace)
    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8", newline="\n") as fh:
        fh.write(line)
        fh.write("\n")
    return p


def iter_traces_jsonl(path: str | Path) -> Iterator[Trace]:
    """Yield :class:`Trace` objects from each non-empty line in a JSONL file."""
    p = Path(path)
    with p.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            yield parse_trace_jsonl_line(line)


def default_trace_path(
    scenario_name: str,
    *,
    base_dir: Path | None = None,
    when: datetime | None = None,
) -> Path:
    """Return ``.agentharness/traces/YYYY-MM-DD/{scenario}_{timestamp}.jsonl`` (AD-008).

    ``scenario_name`` is sanitized for path segments (slashes replaced, length capped).
    """
    dt = when or datetime.now(timezone.utc)
    date_part = dt.strftime("%Y-%m-%d")
    ts = dt.strftime("%Y%m%dT%H%M%S") + "Z"
    safe = scenario_name.replace("/", "_").replace("\\", "_").strip() or "scenario"
    if len(safe) > 200:
        safe = safe[:200]
    root = base_dir if base_dir is not None else Path.cwd() / ".agentharness" / "traces"
    return root / date_part / f"{safe}_{ts}.jsonl"


def write_trace_to_default_location(
    trace: Trace,
    scenario_name: str,
    *,
    base_dir: Path | None = None,
    when: datetime | None = None,
) -> Path:
    """Write ``trace`` to :func:`default_trace_path` and return the path."""
    path = default_trace_path(scenario_name, base_dir=base_dir, when=when)
    return write_trace_jsonl(path, trace)
