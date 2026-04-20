"""Validation tests for LangGraph ToolNode interception (KI-001, KI-005).

Tests both the native wrapper approach (primary) and the AD-002 tool
replacement fallback, for sync and async tools.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool as create_tool
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from agentharness.adapters.langgraph import (
    create_intercepted_tool_node,
    create_intercepted_tool_node_fallback,
)
from agentharness.mocks.interceptor import (
    HarnessInterceptor,
    InterceptMode,
    MockNotConfiguredError,
)


# ── Helper tools used across tests ──────────────────────────────────────


@create_tool
def lookup_order(order_id: str) -> str:
    """Look up an order by ID."""
    return f"Order {order_id}: 2 items, $49.99"


@create_tool
def issue_refund(order_id: str, amount: float) -> str:
    """Issue a refund for an order."""
    return f"Refunded ${amount:.2f} for order {order_id}"


@create_tool
async def async_lookup(order_id: str) -> str:
    """Async version of order lookup."""
    return f"Async Order {order_id}: 3 items, $79.99"


def _tool_call(name: str, args: dict, call_id: str = "call_1"):
    """Build the direct tool-call input format that ToolNode accepts."""
    return [{"name": name, "args": args, "id": call_id, "type": "tool_call"}]


def _runtime_config():
    """Provide the minimal runtime config ToolNode needs outside a graph."""
    return {"configurable": {"__pregel_runtime": Runtime()}}


def _get_messages(result):
    """Extract ToolMessage list from ToolNode result (always a dict)."""
    return result["messages"]


# ═══════════════════════════════════════════════════════════════════════
# Strategy 1: Native wrapper (primary)
# ═══════════════════════════════════════════════════════════════════════


class TestNativeWrapperSync:
    """Sync tool interception via ToolNode's wrap_tool_call parameter."""

    def test_mock_mode_returns_canned_response(self):
        interceptor = HarnessInterceptor(
            mode=InterceptMode.MOCK,
            mock_responses={"lookup_order": "Mocked: order found"},
        )
        tool_node = create_intercepted_tool_node([lookup_order], interceptor)

        result = tool_node.invoke(
            _tool_call("lookup_order", {"order_id": "ORD-123"}),
            config=_runtime_config(),
        )

        msgs = _get_messages(result)
        assert len(msgs) == 1
        assert isinstance(msgs[0], ToolMessage)
        assert "Mocked: order found" in msgs[0].content

        assert len(interceptor.calls) == 1
        record = interceptor.calls[0]
        assert record.tool_name == "lookup_order"
        assert record.args == {"order_id": "ORD-123"}
        assert record.was_mocked is True

    def test_live_mode_calls_real_tool(self):
        interceptor = HarnessInterceptor(mode=InterceptMode.LIVE)
        tool_node = create_intercepted_tool_node([lookup_order], interceptor)

        result = tool_node.invoke(
            _tool_call("lookup_order", {"order_id": "ORD-456"}),
            config=_runtime_config(),
        )

        msgs = _get_messages(result)
        assert len(msgs) == 1
        assert isinstance(msgs[0], ToolMessage)
        assert "ORD-456" in msgs[0].content
        assert "$49.99" in msgs[0].content

        assert len(interceptor.calls) == 1
        record = interceptor.calls[0]
        assert record.tool_name == "lookup_order"
        assert record.was_mocked is False

    def test_mock_mode_raises_when_no_mock_configured(self):
        interceptor = HarnessInterceptor(mode=InterceptMode.MOCK)
        tool_node = create_intercepted_tool_node(
            [lookup_order], interceptor, handle_tool_errors=False,
        )

        with pytest.raises(MockNotConfiguredError):
            tool_node.invoke(
                _tool_call("lookup_order", {"order_id": "ORD-789"}),
                config=_runtime_config(),
            )


class TestNativeWrapperAsync:
    """Async tool interception via ToolNode's awrap_tool_call parameter."""

    @pytest.mark.asyncio
    async def test_async_mock_mode(self):
        interceptor = HarnessInterceptor(
            mode=InterceptMode.MOCK,
            mock_responses={"async_lookup": "Async mocked result"},
        )
        tool_node = create_intercepted_tool_node([async_lookup], interceptor)

        result = await tool_node.ainvoke(
            _tool_call("async_lookup", {"order_id": "ORD-A1"}),
            config=_runtime_config(),
        )

        msgs = _get_messages(result)
        assert len(msgs) == 1
        assert isinstance(msgs[0], ToolMessage)
        assert "Async mocked result" in msgs[0].content

        assert len(interceptor.calls) == 1
        assert interceptor.calls[0].tool_name == "async_lookup"
        assert interceptor.calls[0].was_mocked is True

    @pytest.mark.asyncio
    async def test_async_live_mode(self):
        interceptor = HarnessInterceptor(mode=InterceptMode.LIVE)
        tool_node = create_intercepted_tool_node([async_lookup], interceptor)

        result = await tool_node.ainvoke(
            _tool_call("async_lookup", {"order_id": "ORD-A2"}),
            config=_runtime_config(),
        )

        msgs = _get_messages(result)
        assert len(msgs) == 1
        assert isinstance(msgs[0], ToolMessage)
        assert "ORD-A2" in msgs[0].content
        assert "$79.99" in msgs[0].content

        assert len(interceptor.calls) == 1
        assert interceptor.calls[0].was_mocked is False


class TestNativeWrapperMultiTool:
    """Multiple tools in one ToolNode are each independently intercepted."""

    def test_two_tools_recorded_separately(self):
        interceptor = HarnessInterceptor(
            mode=InterceptMode.MOCK,
            mock_responses={
                "lookup_order": "mock lookup",
                "issue_refund": "mock refund",
            },
        )
        tool_node = create_intercepted_tool_node(
            [lookup_order, issue_refund], interceptor,
        )
        cfg = _runtime_config()

        tool_node.invoke(_tool_call("lookup_order", {"order_id": "ORD-1"}, "c1"), config=cfg)
        tool_node.invoke(
            _tool_call("issue_refund", {"order_id": "ORD-1", "amount": 25.0}, "c2"),
            config=cfg,
        )

        assert len(interceptor.calls) == 2
        assert interceptor.calls[0].tool_name == "lookup_order"
        assert interceptor.calls[1].tool_name == "issue_refund"
        assert interceptor.calls[1].args["amount"] == 25.0


# ═══════════════════════════════════════════════════════════════════════
# Strategy 2: Tool replacement fallback (AD-002)
# ═══════════════════════════════════════════════════════════════════════


class TestFallbackSync:
    """Sync tool interception via tool replacement (AD-002)."""

    def test_fallback_mock_mode(self):
        interceptor = HarnessInterceptor(
            mode=InterceptMode.MOCK,
            mock_responses={"lookup_order": "fallback mock"},
        )
        tool_node = create_intercepted_tool_node_fallback(
            [lookup_order], interceptor,
        )

        result = tool_node.invoke(
            _tool_call("lookup_order", {"order_id": "ORD-F1"}),
            config=_runtime_config(),
        )

        msgs = _get_messages(result)
        assert len(msgs) == 1
        assert isinstance(msgs[0], ToolMessage)

        assert len(interceptor.calls) == 1
        assert interceptor.calls[0].tool_name == "lookup_order"
        assert interceptor.calls[0].was_mocked is True


class TestFallbackAsync:
    """Async tool interception via tool replacement (AD-002)."""

    @pytest.mark.asyncio
    async def test_fallback_async_mock_mode(self):
        interceptor = HarnessInterceptor(
            mode=InterceptMode.MOCK,
            mock_responses={"async_lookup": "fallback async mock"},
        )
        tool_node = create_intercepted_tool_node_fallback(
            [async_lookup], interceptor,
        )

        result = await tool_node.ainvoke(
            _tool_call("async_lookup", {"order_id": "ORD-FA1"}),
            config=_runtime_config(),
        )

        msgs = _get_messages(result)
        assert len(msgs) == 1
        assert isinstance(msgs[0], ToolMessage)

        assert len(interceptor.calls) == 1
        assert interceptor.calls[0].tool_name == "async_lookup"
        assert interceptor.calls[0].was_mocked is True
