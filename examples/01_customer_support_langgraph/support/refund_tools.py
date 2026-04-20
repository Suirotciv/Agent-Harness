"""Mock LangChain tools for the refund agent (AD-005: no real network calls)."""

from __future__ import annotations

import json

from langchain_core.tools import tool as create_tool


@create_tool
def lookup_order(order_id: str) -> str:
    """Fetch order metadata."""
    return json.dumps({"order_id": order_id, "status": "active", "items": 1})


@create_tool
def check_refund_eligibility(order_id: str) -> str:
    """Check if the order is eligible for refund."""
    return json.dumps({"order_id": order_id, "eligible": True, "reason": "within window"})


@create_tool
def calculate_refund(order_id: str, reason: str) -> str:
    """Calculate suggested refund amount."""
    return json.dumps({"order_id": order_id, "reason": reason, "amount": 50.0})


@create_tool
def request_approval(order_id: str, amount: float) -> str:
    """Request human approval for a refund."""
    return json.dumps({"order_id": order_id, "amount": amount, "approval_id": "APR-1"})


@create_tool
def issue_refund(order_id: str, amount: float, approved: bool) -> str:
    """Issue or deny a refund after approval."""
    return json.dumps(
        {"order_id": order_id, "amount": amount, "approved": approved, "status": "issued"}
    )


@create_tool
def escalate_to_human(order_id: str, reason: str) -> str:
    """Escalate when automation cannot proceed."""
    return json.dumps({"order_id": order_id, "reason": reason, "ticket": "HUM-9"})


ALL_REFUND_TOOLS = [
    lookup_order,
    check_refund_eligibility,
    calculate_refund,
    request_approval,
    issue_refund,
    escalate_to_human,
]
