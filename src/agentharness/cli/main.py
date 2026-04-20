"""CLI entry point -- top-level command group for the ``agentharness`` executable."""

from __future__ import annotations

import argparse
import sys


def _stub(_args: argparse.Namespace) -> int:
    sys.stderr.write(
        f"agentharness {_args.command}: not yet implemented (Phase 1+).\n",
    )
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentharness",
        description="AgentHarness — behavioral testing for AI agents (Phase 0 CLI).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser(
        "run",
        help="Run a scenario YAML file and print assertion pass/fail output.",
    )
    run_p.add_argument(
        "scenario",
        type=str,
        metavar="SCENARIO",
        help="Path to a scenario YAML file.",
    )
    run_p.add_argument(
        "--mode",
        choices=("mock", "live"),
        default="mock",
        help="Execution mode (default: mock). AD-005: mock is safe-by-default; live does not enable extra flags in Phase 0.",
    )

    sub.add_parser("watch", help="(Planned) Watch a live agent run.")
    sub.add_parser("record", help="(Planned) Record tool traffic to cassette.")
    sub.add_parser("report", help="(Planned) Generate compliance/report output.")

    return parser


def cli() -> None:
    """Entry point for ``[project.scripts]`` ``agentharness``."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        from agentharness.cli.run import run_command

        code = run_command(args)
        raise SystemExit(code)
    if args.command == "watch":
        raise SystemExit(_stub(args))
    if args.command == "record":
        raise SystemExit(_stub(args))
    if args.command == "report":
        raise SystemExit(_stub(args))
