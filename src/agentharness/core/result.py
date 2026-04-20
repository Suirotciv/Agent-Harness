"""RunResult -- the output of a single scenario execution.

Contains the trace, assertion outcomes, scorer results, and timing data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agentharness.core.trace import Trace


@dataclass
class RunResult:
    """Outcome of running one scenario (trace-first; other fields filled in later phases)."""

    trace: Trace
    scenario_path: str | None = None
    assertion_errors: list[str] = field(default_factory=list)
