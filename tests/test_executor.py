# tests/test_executor.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from taskforge.config.types import ProjectConfig, TaskConfig
from taskforge.executor.executor import Executor
from taskforge.graph.dag import TaskGraph


def _py(cmd: str) -> str:
    """
    Build a shell command that runs `python -c "<cmd>"` using the current interpreter.
    Executor uses shell=True, so return a single command string.
    """
    exe = str(Path(sys.executable))
    # Use double-quotes around the executable path and -c payload to tolerate spaces.
    return f'"{exe}" -c "{cmd}"'


def _project(tasks: dict[str, dict]) -> ProjectConfig:
    """
    tasks schema:
      id -> {command: str, deps?: list[str], env?: dict[str,str], working_dir?: str|None}
    """
    built: dict[str, TaskConfig] = {}
    for tid, spec in tasks.items():
        built[tid] = TaskConfig(
            id=tid,
            command=spec["command"],
            deps=list(spec.get("deps", [])),
            env=dict(spec.get("env", {})),
            working_dir=spec.get("working_dir"),
        )
    return ProjectConfig(tasks=built)


def test_runs_in_dependency_order(tmp_path: Path) -> None:
    log = tmp_path / "log.txt"

    project = _project(
        {
            "a": {"command": _py(f"open(r'{log}','a').write('a\\n')")},
            "b": {"command": _py(f"open(r'{log}','a').write('b\\n')"), "deps": ["a"]},
            "c": {"command": _py(f"open(r'{log}','a').write('c\\n')"), "deps": ["b"]},
        }
    )
    graph = TaskGraph.from_project(project)
    ex = Executor(project, graph)

    rr = ex.run_all()

    assert rr.failed == []
    assert rr.skipped == []
    assert list(rr.results.keys()) == ["a", "b", "c"]
    assert log.read_text(encoding="utf-8").splitlines() == ["a", "b", "c"]


def test_env_is_applied(tmp_path: Path) -> None:
    project = _project(
        {
            "envtask": {
                "env": {"TF_TEST": "ok"},
                "command": _py(
                    "import os; raise SystemExit(0 if os.environ.get('TF_TEST')=='ok' else 2)"
                ),
            }
        }
    )
    graph = TaskGraph.from_project(project)
    ex = Executor(project, graph)

    rr = ex.run_all()

    assert rr.failed == []
    assert rr.skipped == []
    assert rr.results["envtask"].returncode == 0


def test_working_dir_is_respected(tmp_path: Path) -> None:
    wd = tmp_path / "wd"
    wd.mkdir()
    out = wd / "written.txt"

    project = _project(
        {
            "w": {
                "working_dir": str(wd),
                "command": _py(
                    "from pathlib import Path; Path('written.txt').write_text('ok', encoding='utf-8')"
                ),
            }
        }
    )
    graph = TaskGraph.from_project(project)
    ex = Executor(project, graph)

    rr = ex.run_all()

    assert rr.failed == []
    assert rr.skipped == []
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "ok"


def test_failure_skips_dependents_fail_fast_false(tmp_path: Path) -> None:
    log = tmp_path / "log.txt"

    project = _project(
        {
            "a_fail": {
                "command": _py(
                    f"open(r'{log}','a').write('a_fail\\n'); raise SystemExit(7)"
                )
            },
            "b_dep": {
                "deps": ["a_fail"],
                "command": _py(f"open(r'{log}','a').write('b_dep\\n')"),
            },
            "c_ind": {
                "command": _py(f"open(r'{log}','a').write('c_ind\\n')"),
            },
        }
    )
    graph = TaskGraph.from_project(project)
    ex = Executor(project, graph)

    rr = ex.run_all(fail_fast=False)

    assert rr.failed == ["a_fail"]
    assert rr.skipped == ["b_dep"]
    assert list(rr.results.keys()) == ["a_fail", "c_ind"]
    assert log.read_text(encoding="utf-8").splitlines() == ["a_fail", "c_ind"]


def test_fail_fast_true_marks_remaining_as_skipped(tmp_path: Path) -> None:
    log = tmp_path / "log.txt"

    project = _project(
        {
            "a_fail": {
                "command": _py(
                    f"open(r'{log}','a').write('a_fail\\n'); raise SystemExit(3)"
                )
            },
            "b_dep": {
                "deps": ["a_fail"],
                "command": _py(f"open(r'{log}','a').write('b_dep\\n')"),
            },
            "c_ind": {
                "command": _py(f"open(r'{log}','a').write('c_ind\\n')"),
            },
        }
    )
    graph = TaskGraph.from_project(project)
    ex = Executor(project, graph)

    rr = ex.run_all(fail_fast=True)

    assert rr.failed == ["a_fail"]
    # Both tasks after the failure are skipped (regardless of dependency).
    assert rr.skipped == ["b_dep", "c_ind"]
    assert list(rr.results.keys()) == ["a_fail"]
    assert log.read_text(encoding="utf-8").splitlines() == ["a_fail"]


def test_run_target_executes_only_needed_subgraph(tmp_path: Path) -> None:
    log = tmp_path / "log.txt"

    project = _project(
        {
            "a": {"command": _py(f"open(r'{log}','a').write('a\\n')")},
            "b": {"deps": ["a"], "command": _py(f"open(r'{log}','a').write('b\\n')")},
            "c": {"deps": ["b"], "command": _py(f"open(r'{log}','a').write('c\\n')")},
            "d_extra": {"command": _py(f"open(r'{log}','a').write('d_extra\\n')")},
        }
    )
    graph = TaskGraph.from_project(project)
    ex = Executor(project, graph)

    rr = ex.run_target("c")

    assert rr.failed == []
    assert rr.skipped == []
    assert list(rr.results.keys()) == ["a", "b", "c"]
    assert "d_extra" not in rr.results
    assert log.read_text(encoding="utf-8").splitlines() == ["a", "b", "c"]
