import os
import subprocess
import time

from taskforge.config import ProjectConfig
from taskforge.graph import TaskGraph

from .types import RunResult, TaskResult


class Executor:
    def __init__(self, project: ProjectConfig, graph: TaskGraph):
        self.project = project
        self.graph = graph

    def _run(self, order: list[str], *, fail_fast: bool) -> RunResult:
        results: dict[str, TaskResult] = {}
        failed_list: list[str] = []
        failed_set: set[str] = set()
        skipped_list: list[str] = []
        skipped_set: set[str] = set()
        succeeded_set: set[str] = (
            set()
        )  # Unused for now, can be useful with parallel mode
        processed: set[str] = set()
        stopped_early: bool = False

        for tid in order:
            task = self.project.get_task(tid)
            if any(dep in failed_set or dep in skipped_set for dep in task.deps):
                skipped_list.append(tid)
                skipped_set.add(tid)
                processed.add(tid)
                continue

            start = time.monotonic()
            result = subprocess.run(
                task.command,
                shell=True,
                cwd=task.working_dir or None,
                env={**os.environ, **task.env},
                capture_output=True,
                text=True,
            )
            duration = time.monotonic() - start

            results[tid] = TaskResult(
                tid, result.returncode, result.stdout, result.stderr, duration
            )

            if result.returncode == 0:
                succeeded_set.add(tid)
                processed.add(tid)
            else:
                failed_list.append(tid)
                failed_set.add(tid)
                processed.add(tid)
                if fail_fast:
                    stopped_early = True
                    break

        if stopped_early:
            for tid in order:
                if tid not in processed:
                    skipped_list.append(tid)
                    skipped_set.add(tid)

        return RunResult(order, results, failed_list, skipped_list)

    def run_all(self, *, fail_fast: bool = True) -> RunResult:
        order = self.graph.topo_order()
        return self._run(order, fail_fast=fail_fast)

    def run_target(self, target: str, *, fail_fast: bool = True) -> RunResult:
        order = self.graph.subgraph_order(target)
        return self._run(order, fail_fast=fail_fast)
