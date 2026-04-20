"""Reporting package — formatters live in submodules.

Console, JSON, HTML, and other reporters are implemented in ``console.py``,
``json_report.py``, etc. Import formatters **from those submodules** directly
(e.g. ``from agentharness.reporting.console import ConsoleReporter``). This
package root intentionally does **not** re-export them, to avoid circular
imports as reporting grows and to keep optional heavy dependencies isolated.
"""
