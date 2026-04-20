"""Resource assertions (Tests 4.1-4.3).

assert_cost_under, assert_latency_p95_under, assert_token_efficiency.
Verifies the agent operated within its resource budget.
"""

from __future__ import annotations

from agentharness.assertions.base import REFS_ASSERT_COST_UNDER, AssertionResult, finish
from agentharness.core.trace import Trace

# Trace-level keys (harness.* and common gen_ai usage fallbacks)
_HARNESS_COST_USD = "harness.estimated_cost_usd"
_GEN_AI_MODEL = "gen_ai.request.model"
_HARNESS_IN = "harness.input_tokens"
_HARNESS_OUT = "harness.output_tokens"
_GEN_AI_IN = "gen_ai.usage.prompt_tokens"
_GEN_AI_OUT = "gen_ai.usage.completion_tokens"


def _resolve_cost_usd(trace: Trace, model: str | None) -> float | None:
    """Resolve USD cost from explicit attribute or tokencost + token counts."""
    raw = trace.attributes.get(_HARNESS_COST_USD)
    if raw is not None:
        return float(raw)

    m = model or trace.attributes.get(_GEN_AI_MODEL)
    if not m or not isinstance(m, str):
        return None

    in_t = trace.attributes.get(_HARNESS_IN)
    if in_t is None:
        in_t = trace.attributes.get(_GEN_AI_IN)
    out_t = trace.attributes.get(_HARNESS_OUT)
    if out_t is None:
        out_t = trace.attributes.get(_GEN_AI_OUT)
    if in_t is None or out_t is None:
        return None

    try:
        from tokencost import calculate_cost_by_tokens  # type: ignore[import-untyped]
    except ImportError:
        return None

    inp = calculate_cost_by_tokens(int(in_t), m, "input")
    outp = calculate_cost_by_tokens(int(out_t), m, "output")
    return float(inp + outp)


def assert_cost_under(
    trace: Trace,
    *,
    max_usd: float,
    model: str | None = None,
) -> AssertionResult:
    """Assert estimated trace cost is at most ``max_usd`` (USD).

    Resolution order:

    1. ``trace.attributes['harness.estimated_cost_usd']`` if set.
    2. Else, if optional dependency **tokencost** is installed and the trace
       carries a model id plus input/output token counts (``harness.input_tokens`` /
       ``harness.output_tokens`` or ``gen_ai.usage.*``), compute cost via
       :func:`tokencost.calculate_cost_by_tokens`.

    Raises:
        AssertionError: If cost cannot be determined or exceeds ``max_usd``.
    """
    if max_usd < 0:
        raise ValueError("assert_cost_under: max_usd must be non-negative")

    cost = _resolve_cost_usd(trace, model)
    if cost is None:
        msg = (
            "assert_cost_under: could not resolve cost. Set "
            f"trace.attributes[{_HARNESS_COST_USD!r}], or set model + input/output "
            f"token counts ({_HARNESS_IN!r}/{_HARNESS_OUT!r} or {_GEN_AI_IN!r}/{_GEN_AI_OUT!r}) "
            "and pip install tokencost (see agentharness[resource])."
        )
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_cost_under",
                tool=None,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_COST_UNDER),
                details={
                    "trace_id": trace.trace_id,
                    "max_usd": max_usd,
                    "actual_cost_usd": None,
                    "constraint": "trace cost must be resolvable and <= max_usd",
                },
            )
        )
    if cost > float(max_usd):
        msg = f"assert_cost_under: cost {cost:.6f} USD exceeds max_usd={max_usd}"
        return finish(
            AssertionResult(
                passed=False,
                assertion_name="assert_cost_under",
                tool=None,
                message=msg,
                regulatory_refs=list(REFS_ASSERT_COST_UNDER),
                details={
                    "trace_id": trace.trace_id,
                    "cost_usd": cost,
                    "actual_cost_usd": cost,
                    "max_usd": max_usd,
                    "constraint": "estimated_cost_usd must be <= max_usd",
                },
            )
        )
    ok_msg = (
        f"assert_cost_under passed: cost {cost:.6f} USD is at most max_usd={max_usd} "
        f"(trace_id={trace.trace_id!r})."
    )
    return finish(
        AssertionResult(
            passed=True,
            assertion_name="assert_cost_under",
            tool=None,
            message=ok_msg,
            regulatory_refs=list(REFS_ASSERT_COST_UNDER),
            details={
                "trace_id": trace.trace_id,
                "cost_usd": cost,
                "actual_cost_usd": cost,
                "max_usd": max_usd,
                "constraint": "estimated_cost_usd must be <= max_usd",
            },
        )
    )
