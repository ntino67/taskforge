from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from taskforge.config.types import ProjectConfig

from .types import CycleError


class _Visit(Enum):
    UNVISITED = auto()
    VISITING = auto()
    VISITED = auto()


@dataclass(frozen=True)
class TaskGraph:
    project: ProjectConfig
    _deps: dict[str, tuple[str, ...]]

    @classmethod
    def from_project(cls, project: ProjectConfig) -> TaskGraph:
        deps = {}
        tasks_ids = project.tasks_ids()
        for task_id in tasks_ids:
            task = project.get_task(task_id)
            deps_tuple = tuple(sorted(task.deps))
            deps[task_id] = deps_tuple

        return cls(project, deps)

    def topo_order(self) -> list[str]:
        return self._toposort(set(self._deps))

    def subgraph_order(self, target: str) -> list[str]:
        if target not in self._deps:
            raise KeyError(target)

        needed: set[str] = set()
        worklist: list[str] = [target]

        while worklist:
            task_id = worklist.pop()
            if task_id in needed:
                continue
            needed.add(task_id)
            for dep in self._deps[task_id]:
                worklist.append(dep)

        return self._toposort(needed)

    def _toposort(self, universe: set[str]) -> list[str]:
        state = {tid: _Visit.UNVISITED for tid in universe}
        out: list[str] = []
        stack: list[str] = []
        pos: dict[str, int] = {}

        def visit(tid: str) -> None:
            if state[tid] == _Visit.VISITING:
                start = pos[tid]
                raise CycleError(stack[start:] + [tid])
            if state[tid] == _Visit.VISITED:
                return

            state[tid] = _Visit.VISITING
            pos[tid] = len(stack)
            stack.append(tid)

            for dep in self._deps[tid]:
                if dep in state:
                    visit(dep)

            stack.pop()
            pos.pop(tid)
            state[tid] = _Visit.VISITED
            out.append(tid)

        for tid in sorted(universe):
            visit(tid)

        return out
