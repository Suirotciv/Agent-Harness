"""LangGraph adapter -- ToolNode interception, interrupt handling, and checkpointer integration.

Provides two interception strategies:

1. **Native wrapper (primary):** Uses ToolNode's built-in ``wrap_tool_call`` /
   ``awrap_tool_call`` parameters. Clean, stable, no patching. Requires a
   LangGraph version that exposes these parameters.

2. **Tool replacement (fallback, AD-002):** Replaces tool callables at
   instantiation time before passing them to ToolNode. Works on any
   LangGraph version but requires more care to preserve tool metadata.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from agentharness.mocks.interceptor import HarnessInterceptor, InterceptMode

if TYPE_CHECKING:
    from langchain_core.messages import ToolMessage
    from langchain_core.tools import BaseTool
    from langgraph.prebuilt.tool_node import (
        AsyncToolCallWrapper,
        ToolCallRequest,
        ToolCallWrapper,
    )
    from langgraph.types import Command


# ---------------------------------------------------------------------------
# Strategy 1: Native wrapper (primary)
# ---------------------------------------------------------------------------

def make_sync_wrapper(interceptor: HarnessInterceptor) -> ToolCallWrapper:
    """Create a sync ``ToolCallWrapper`` that delegates to *interceptor*.

    The returned callable has the signature LangGraph expects::

        (ToolCallRequest, execute) -> ToolMessage | Command
    """

    def wrapper(
        request: ToolCallRequest,
        execute: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        from langchain_core.messages import ToolMessage as TM

        tool_name = request.tool_call["name"]
        args = request.tool_call["args"]
        tool_call_id = request.tool_call["id"]

        if interceptor.mode is InterceptMode.MOCK:
            mock_response = interceptor.intercept_sync(
                tool_name, args, tool_call_id,
            )
            content = (
                mock_response
                if isinstance(mock_response, str)
                else json.dumps(mock_response, ensure_ascii=False)
            )
            return TM(content=content, tool_call_id=tool_call_id, name=tool_name)

        # LIVE mode -- delegate to the real tool via execute()
        def _execute_real() -> ToolMessage | Command:
            return execute(request)

        result = interceptor.intercept_sync(
            tool_name, args, tool_call_id, execute_real=_execute_real,
        )
        return result

    return wrapper


def make_async_wrapper(interceptor: HarnessInterceptor) -> AsyncToolCallWrapper:
    """Create an async ``AsyncToolCallWrapper`` that delegates to *interceptor*."""

    async def wrapper(
        request: ToolCallRequest,
        execute: Any,
    ) -> ToolMessage | Command:
        from langchain_core.messages import ToolMessage as TM

        tool_name = request.tool_call["name"]
        args = request.tool_call["args"]
        tool_call_id = request.tool_call["id"]

        if interceptor.mode is InterceptMode.MOCK:
            mock_response = await interceptor.intercept_async(
                tool_name, args, tool_call_id,
            )
            content = (
                mock_response
                if isinstance(mock_response, str)
                else json.dumps(mock_response, ensure_ascii=False)
            )
            return TM(content=content, tool_call_id=tool_call_id, name=tool_name)

        async def _execute_real() -> ToolMessage | Command:
            return await execute(request)

        result = await interceptor.intercept_async(
            tool_name, args, tool_call_id, execute_real=_execute_real,
        )
        return result

    return wrapper


def create_intercepted_tool_node(
    tools: Sequence[BaseTool | Callable[..., Any]],
    interceptor: HarnessInterceptor,
    **toolnode_kwargs: Any,
) -> Any:
    """Build a ToolNode with the interceptor wired in via native wrappers.

    This is the primary (recommended) approach.

    Args:
        tools: Tools to register with the ToolNode.
        interceptor: The HarnessInterceptor that will record/mock calls.
        **toolnode_kwargs: Extra keyword arguments forwarded to ToolNode
            (e.g. ``handle_tool_errors``, ``messages_key``).

    Returns:
        A configured ``ToolNode`` instance.
    """
    from langgraph.prebuilt import ToolNode

    return ToolNode(
        tools,
        wrap_tool_call=make_sync_wrapper(interceptor),
        awrap_tool_call=make_async_wrapper(interceptor),
        **toolnode_kwargs,
    )


# ---------------------------------------------------------------------------
# Strategy 2: Tool replacement (fallback, AD-002)
# ---------------------------------------------------------------------------

def make_replacement_tool(
    original_tool: BaseTool,
    interceptor: HarnessInterceptor,
) -> BaseTool:
    """Create a replacement tool that intercepts calls while preserving metadata.

    The replacement has the same name, description, and args schema as the
    original. Only the execution path is swapped.

    This is the AD-002 fallback for LangGraph versions that do not expose
    ``wrap_tool_call`` / ``awrap_tool_call``.
    """
    from langchain_core.tools import StructuredTool

    original_name = original_tool.name
    call_counter = {"n": 0}

    def _intercepted_func(**kwargs: Any) -> Any:
        call_counter["n"] += 1
        tool_call_id = f"{original_name}_fallback_{call_counter['n']}"

        if interceptor.mode is InterceptMode.MOCK:
            return interceptor.intercept_sync(
                original_name, kwargs, tool_call_id,
            )

        def _run_original() -> Any:
            return original_tool.invoke(
                {"name": original_name, "args": kwargs, "id": tool_call_id, "type": "tool_call"}
            )

        return interceptor.intercept_sync(
            original_name, kwargs, tool_call_id, execute_real=_run_original,
        )

    async def _intercepted_afunc(**kwargs: Any) -> Any:
        call_counter["n"] += 1
        tool_call_id = f"{original_name}_fallback_{call_counter['n']}"

        if interceptor.mode is InterceptMode.MOCK:
            return await interceptor.intercept_async(
                original_name, kwargs, tool_call_id,
            )

        async def _run_original() -> Any:
            return await original_tool.ainvoke(
                {"name": original_name, "args": kwargs, "id": tool_call_id, "type": "tool_call"}
            )

        return await interceptor.intercept_async(
            original_name, kwargs, tool_call_id, execute_real=_run_original,
        )

    return StructuredTool.from_function(
        func=_intercepted_func,
        coroutine=_intercepted_afunc,
        name=original_tool.name,
        description=original_tool.description or "",
        args_schema=original_tool.args_schema,
    )


def create_intercepted_tool_node_fallback(
    tools: Sequence[BaseTool],
    interceptor: HarnessInterceptor,
    **toolnode_kwargs: Any,
) -> Any:
    """Build a ToolNode using tool replacement (AD-002 fallback).

    Each tool is replaced with an intercepted version before being passed
    to ToolNode. No ``wrap_tool_call`` parameter is used.

    Args:
        tools: Original BaseTool instances.
        interceptor: The HarnessInterceptor that will record/mock calls.
        **toolnode_kwargs: Extra keyword arguments forwarded to ToolNode.

    Returns:
        A configured ``ToolNode`` instance with replaced tools.
    """
    from langgraph.prebuilt import ToolNode

    replaced = [make_replacement_tool(t, interceptor) for t in tools]
    return ToolNode(replaced, **toolnode_kwargs)
