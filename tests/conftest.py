"""Shared pytest fixtures for Agent-Harness test suite.

The ``agentharness`` pytest plugin (``pytest11`` entry point → ``agentharness.pytest_plugin``)
registers the ``run`` fixture for tests decorated with ``@scenario``. No extra
``pytest_plugins`` import is required when the package is installed editable.
"""

pytest_plugins = ["pytester"]
