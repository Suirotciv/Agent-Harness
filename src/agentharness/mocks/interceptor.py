"""Tool interceptor -- wraps sync and async callables to record calls and return mock responses.

This is the most critical piece of the harness. It sits between the agent
and real tool functions, capturing arguments and responses without modifying
the agent's source code.

The HarnessInterceptor is framework-agnostic. Framework adapters (LangGraph,
OpenAI, etc.) create thin wrappers that bridge this class to their specific
hook points.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agentharness.mocks.cassette import Cassette, normalize_args


class InterceptMode(Enum):
    """Execution mode for intercepted tool calls."""

    MOCK = "mock"
    LIVE = "live"
    REPLAY = "replay"


@dataclass
class ToolCallRecord:
    """A single recorded tool call with timing and response data.

    Captured by HarnessInterceptor during scenario execution. These records
    form the raw material for the trace and all assertion evaluation.
    """

    tool_name: str
    args: dict[str, Any]
    tool_call_id: str
    response: Any = None
    error: str | None = None
    timestamp: float = field(default_factory=time.monotonic)
    duration_ms: float | None = None
    was_mocked: bool = False


class MockNotConfiguredError(Exception):
    """Raised when a tool is called in mock mode but no mock response is registered.

    This is a loud failure by design (AD-005). We never silently pass through
    to a real tool call when in mock mode.
    """

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(
            f"Tool '{tool_name}' was called in mock mode but no mock response "
            f"is configured. Register a mock response or switch to live mode."
        )


class ReplayCassetteError(Exception):
    """Raised in REPLAY mode when no cassette entry matches tool name + args (AD-005)."""

    def __init__(self, tool_name: str, tool_args: dict[str, Any]) -> None:
        self.tool_name = tool_name
        self.tool_args = tool_args
        super().__init__(
            f"No cassette entry found for tool '{tool_name}' with args {tool_args!r}. "
            "Re-record the cassette or add a manual entry."
        )


class HarnessInterceptor:
    """Records tool calls and routes execution based on mode.

    In MOCK mode, returns pre-configured responses from the mock registry.
    In LIVE mode, delegates to the real tool and records the response.
    In REPLAY mode, returns responses from a loaded :class:`~agentharness.mocks.cassette.Cassette`.

    This class has no framework-specific knowledge. Adapters provide the
    bridge between this class and framework-specific hook points (e.g.
    LangGraph's wrap_tool_call, OpenAI function call interception, etc.).
    """

    def __init__(
        self,
        *,
        mode: InterceptMode = InterceptMode.MOCK,
        mock_responses: dict[str, Any] | None = None,
        cassette: Cassette | None = None,
    ) -> None:
        self.mode = mode
        self.mock_responses: dict[str, Any] = mock_responses or {}
        self.cassette: Cassette | None = cassette
        self.calls: list[ToolCallRecord] = []
        if mode is InterceptMode.REPLAY and cassette is None:
            msg = "REPLAY mode requires a cassette"
            raise ValueError(msg)

    def record_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_call_id: str,
        *,
        response: Any = None,
        error: str | None = None,
        duration_ms: float | None = None,
        was_mocked: bool = False,
    ) -> ToolCallRecord:
        """Append a ToolCallRecord and return it."""
        record = ToolCallRecord(
            tool_name=tool_name,
            args=args,
            tool_call_id=tool_call_id,
            response=response,
            error=error,
            duration_ms=duration_ms,
            was_mocked=was_mocked,
        )
        self.calls.append(record)
        return record

    def get_mock_response(self, tool_name: str) -> Any:
        """Look up the pre-configured mock response for a tool.

        Raises MockNotConfiguredError if no mock is registered.
        """
        if tool_name not in self.mock_responses:
            raise MockNotConfiguredError(tool_name)
        return self.mock_responses[tool_name]

    def has_mock(self, tool_name: str) -> bool:
        """Check whether a mock response is registered for this tool."""
        return tool_name in self.mock_responses

    # ------------------------------------------------------------------
    # Generic sync/async intercept helpers
    #
    # These are the building blocks that framework adapters call.
    # They handle recording + mode routing but know nothing about
    # ToolMessage, ToolCallRequest, or any framework type.
    # ------------------------------------------------------------------

    def intercept_sync(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_call_id: str,
        execute_real: Any | None = None,
    ) -> Any:
        """Synchronous interception point.

        Args:
            tool_name: Name of the tool being called.
            args: Arguments the agent passed to the tool.
            tool_call_id: Unique ID for this tool call.
            execute_real: A zero-arg callable that invokes the real tool
                and returns its response. Required in LIVE mode.

        Returns:
            The tool response (real or mocked).

        Raises:
            MockNotConfiguredError: If mode is MOCK and no response is registered.
        """
        start = time.monotonic()

        if self.mode is InterceptMode.REPLAY:
            assert self.cassette is not None
            norm = normalize_args(args)
            response = self.cassette.lookup(tool_name, norm)
            if response is None:
                raise ReplayCassetteError(tool_name, norm)
            duration = (time.monotonic() - start) * 1000
            self.record_call(
                tool_name,
                args,
                tool_call_id,
                response=response,
                duration_ms=duration,
                was_mocked=True,
            )
            return response

        if self.mode is InterceptMode.MOCK:
            response = self.get_mock_response(tool_name)
            duration = (time.monotonic() - start) * 1000
            self.record_call(
                tool_name,
                args,
                tool_call_id,
                response=response,
                duration_ms=duration,
                was_mocked=True,
            )
            return response

        # LIVE mode -- call the real tool
        if execute_real is None:
            raise ValueError("execute_real callable is required in LIVE mode.")

        try:
            response = execute_real()
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(
                tool_name,
                args,
                tool_call_id,
                error=str(exc),
                duration_ms=duration,
            )
            raise

        duration = (time.monotonic() - start) * 1000
        self.record_call(
            tool_name,
            args,
            tool_call_id,
            response=response,
            duration_ms=duration,
        )
        return response

    async def intercept_async(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_call_id: str,
        execute_real: Any | None = None,
    ) -> Any:
        """Asynchronous interception point.

        Same contract as intercept_sync but awaits execute_real.
        """
        start = time.monotonic()

        if self.mode is InterceptMode.REPLAY:
            assert self.cassette is not None
            norm = normalize_args(args)
            response = self.cassette.lookup(tool_name, norm)
            if response is None:
                raise ReplayCassetteError(tool_name, norm)
            duration = (time.monotonic() - start) * 1000
            self.record_call(
                tool_name,
                args,
                tool_call_id,
                response=response,
                duration_ms=duration,
                was_mocked=True,
            )
            return response

        if self.mode is InterceptMode.MOCK:
            response = self.get_mock_response(tool_name)
            duration = (time.monotonic() - start) * 1000
            self.record_call(
                tool_name,
                args,
                tool_call_id,
                response=response,
                duration_ms=duration,
                was_mocked=True,
            )
            return response

        if execute_real is None:
            raise ValueError("execute_real callable is required in LIVE mode.")

        try:
            response = await execute_real()
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(
                tool_name,
                args,
                tool_call_id,
                error=str(exc),
                duration_ms=duration,
            )
            raise

        duration = (time.monotonic() - start) * 1000
        self.record_call(
            tool_name,
            args,
            tool_call_id,
            response=response,
            duration_ms=duration,
        )
        return response

    def reset(self) -> None:
        """Clear all recorded calls. Useful between test scenarios."""
        self.calls.clear()
