"""Trace and Span models (OpenInference-compatible).

Structured trace format for tool calls, LLM calls, and harness metadata.
Uses Pydantic v2 (AD-003, Phase 0 sprint). Timestamps follow OTLP: Unix epoch
nanoseconds as integers (``start_time_unix_nano`` / ``end_time_unix_nano``).
"""

from __future__ import annotations

import secrets
import time
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentharness.telemetry import schema as trace_schema

SpanStatusCode = Literal["UNSET", "OK", "ERROR"]


def new_trace_id() -> str:
    """Return a 128-bit trace id as 32 lowercase hex chars (OTLP style)."""
    return uuid4().hex


def new_span_id() -> str:
    """Return a 64-bit span id as 16 lowercase hex chars (OTLP style)."""
    return secrets.token_hex(8)


def utc_now_unix_nano() -> int:
    """Current UTC time in Unix epoch nanoseconds."""
    return time.time_ns()


class Span(BaseModel):
    """A single span in a trace (OTLP-aligned identifiers and timestamps)."""

    model_config = ConfigDict(extra="allow")

    trace_id: str = Field(min_length=1, description="32-char hex trace id")
    span_id: str = Field(min_length=1, description="16-char hex span id")
    parent_span_id: str | None = Field(
        default=None,
        description="16-char hex parent span id, if any",
    )
    name: str
    kind: str = Field(
        default=trace_schema.SPAN_KIND_CHAIN,
        description="Usually openinference.span.kind value, e.g. TOOL, LLM",
    )
    start_time_unix_nano: int
    end_time_unix_nano: int | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    status_code: SpanStatusCode = trace_schema.STATUS_UNSET
    status_message: str | None = None


class Trace(BaseModel):
    """Complete trace: metadata plus ordered spans for one agent run."""

    model_config = ConfigDict(extra="allow")

    trace_id: str = Field(default_factory=new_trace_id)
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Trace-level metadata (harness.*, gen_ai.*, etc.)",
    )
    spans: list[Span] = Field(default_factory=list)

    @model_validator(mode="after")
    def _spans_match_trace_id(self) -> Trace:
        for i, span in enumerate(self.spans):
            if span.trace_id != self.trace_id:
                msg = (
                    f"spans[{i}].trace_id {span.trace_id!r} != "
                    f"trace.trace_id {self.trace_id!r}"
                )
                raise ValueError(msg)
        return self

    def add_span(self, span: Span) -> Span:
        """Append a span after checking ``trace_id`` matches this trace."""
        if span.trace_id != self.trace_id:
            raise ValueError(
                f"span.trace_id {span.trace_id!r} != trace.trace_id {self.trace_id!r}"
            )
        self.spans.append(span)
        return span
