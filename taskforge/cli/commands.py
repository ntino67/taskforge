from __future__ import annotations

import argparse
import sys

from taskforge.config import ConfigError, load_project
from taskforge.executor import Executor, RunResult
from taskforge.graph import GraphError, TaskGraph

from .args import build_parser


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)

        match args.command:
            case "run":
                return cmd_run(args)
            case "list":
                return cmd_list(args)
            case "graph":
                return cmd_graph(args)
            case _:
                return 2

    except (ConfigError, GraphError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    except KeyboardInterrupt:
        return 130


def cmd_run(args: argparse.Namespace) -> int:
    rr = _run_with(args)
    _print_result(rr)
    return 1 if rr.failed else 0


def cmd_list(args: argparse.Namespace) -> int:
    project = load_project(args.config)
    for tid in project.tasks_ids():
        print(tid)
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    project = load_project(args.config)
    for tid in project.tasks_ids():
        task = project.get_task(tid)
        deps = " ".join(sorted(task.deps))
        print(f"{tid}: {deps}".rstrip())
    return 0


def _run_with(args: argparse.Namespace) -> RunResult:
    project = load_project(args.config)
    graph = TaskGraph.from_project(project)
    executor = Executor(project, graph)
    fail_fast = not args.no_fail_fast
    targets: list[str] = args.targets

    if len(targets) == 0:
        return executor.run_all(fail_fast=fail_fast)
    if len(targets) == 1:
        return executor.run_target(targets[0], fail_fast=fail_fast)
    raise ConfigError("multiple targets not supported yet")


def _print_result(rr: RunResult) -> None:
    for tid in rr.order:
        if tid in rr.results:
            result = rr.results[tid]
            if result.returncode == 0:
                print(
                    f"OK {tid}, {result.duration_s:.3f}s, exit code = {result.returncode}"
                )
            else:
                print(
                    f"FAIL {tid}, {result.duration_s:.3f}s, exit code = {result.returncode}"
                )
        else:
            print(f"SKIP {tid}")
