"""Trace schema definitions (OpenInference-compatible).

Canonical field names for span attributes and trace resource-style metadata.
Harness-specific keys use the ``harness.*`` namespace (AD-003).

Values for ``openinference.span.kind`` follow OpenInference (uppercase strings).
OpenTelemetry ``gen_ai.*`` keys follow the experimental semantic conventions
where we surface model/system metadata on the trace.
"""

from __future__ import annotations

# --- harness.* (AD-003) ---
HARNESS_SCENARIO_ID = "harness.scenario_id"
HARNESS_MODE = "harness.mode"
HARNESS_SEED = "harness.seed"
HARNESS_RUN_ID = "harness.run_id"

# --- OpenTelemetry gen_ai (experimental; trace-level attributes) ---
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"

# --- OpenInference span attributes ---
# See: https://github.com/Arize-ai/openinference/tree/main/spec
OPENINFERENCE_SPAN_KIND = "openinference.span.kind"

# Common ``openinference.span.kind`` values
SPAN_KIND_LLM = "LLM"
SPAN_KIND_TOOL = "TOOL"
SPAN_KIND_CHAIN = "CHAIN"
SPAN_KIND_AGENT = "AGENT"

TOOL_NAME = "tool.name"

INPUT_VALUE = "input.value"
OUTPUT_VALUE = "output.value"
INPUT_MIME_TYPE = "input.mime_type"
OUTPUT_MIME_TYPE = "output.mime_type"

# OTLP-style span status codes (string form for JSON traces)
STATUS_UNSET = "UNSET"
STATUS_OK = "OK"
STATUS_ERROR = "ERROR"
