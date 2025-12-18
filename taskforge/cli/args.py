from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taskforge")

    parser.add_argument(
        "--config",
        default="taskforge.yml",
        help="Path to config file",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # run
    run = subparsers.add_parser("run", help="Run tasks")
    run.add_argument(
        "targets",
        nargs="*",
        help="Target task ids",
    )
    run.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue executing independent tasks after failure",
    )

    # list
    subparsers.add_parser("list", help="List tasks")

    # graph
    subparsers.add_parser("graph", help="Show dependency graph")

    return parser
