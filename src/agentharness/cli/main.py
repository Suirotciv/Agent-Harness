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
    run_p.add_argument(
        "--replay",
        nargs="?",
        const="",
        default=None,
        metavar="CASSETTE",
        help=(
            "Replay tool responses from a cassette JSON file. Optional path "
            "(default: cassettes/<scenario_stem>.json under cwd). Forces replay mode."
        ),
    )
    run_p.add_argument(
        "--diff",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Baseline trace: cassette JSON (.json) or trace JSONL (.jsonl). "
            "After the run, compare the candidate trace to this baseline (informational)."
        ),
    )
    run_p.add_argument(
        "--diff-mode",
        choices=("strict", "subset", "superset"),
        default="strict",
        help="How to compare baseline vs candidate when --diff is set (default: strict).",
    )

    sub.add_parser("watch", help="(Planned) Watch a live agent run.")
    record_p = sub.add_parser(
        "record",
        help="Record tool traffic from a scenario run to a cassette JSON file.",
    )
    record_p.add_argument(
        "scenario",
        type=str,
        metavar="SCENARIO",
        help="Path to a scenario YAML file.",
    )
    record_p.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        metavar="PATH",
        help="Cassette output path (default: cassettes/<scenario_stem>.json under cwd).",
    )
    record_p.add_argument(
        "--mode",
        choices=("live", "mock"),
        default="live",
        help="Execution mode (default: live). AD-005: live requires --allow-real-tools.",
    )
    record_p.add_argument(
        "--allow-sensitive-recording",
        action="store_true",
        help="Disable PII scrubbing in the saved cassette (secrets still scrubbed).",
    )
    record_p.add_argument(
        "--allow-real-tools",
        action="store_true",
        help="Required with --mode live to confirm intentional real tool execution.",
    )
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
        from agentharness.cli.record import record_command

        code = record_command(args)
        raise SystemExit(code)
    if args.command == "report":
        raise SystemExit(_stub(args))
