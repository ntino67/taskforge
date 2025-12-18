# tests/test_cli.py
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from taskforge.cli import run_cli


def _py(code: str) -> str:
    exe = str(Path(sys.executable))
    # This returns a shell command string. JSON will escape it safely.
    return f'"{exe}" -c "{code}"'


def _write_json_config(path: Path, tasks: dict) -> None:
    path.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")


def test_list_prints_one_task_per_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "taskforge.json"
    _write_json_config(
        cfg,
        {
            "b": {"command": _py("raise SystemExit(0)")},
            "a": {"command": _py("raise SystemExit(0)")},
        },
    )

    code = run_cli(["--config", str(cfg), "list"])
    out = capsys.readouterr().out.splitlines()

    assert code == 0
    assert out == ["a", "b"]


def test_graph_prints_adjacency_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "taskforge.json"
    _write_json_config(
        cfg,
        {
            "c": {"command": _py("raise SystemExit(0)"), "deps": ["b", "a"]},
            "b": {"command": _py("raise SystemExit(0)"), "deps": ["a"]},
            "a": {"command": _py("raise SystemExit(0)")},
        },
    )

    code = run_cli(["--config", str(cfg), "graph"])
    out = capsys.readouterr().out.splitlines()

    assert code == 0
    assert out == ["a:", "b: a", "c: a b"]


def test_run_all_executes_and_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "taskforge.json"
    log = tmp_path / "log.txt"

    _write_json_config(
        cfg,
        {
            "a": {"command": _py(f"open(r'{log}','a').write('a\\\\n')")},
            "b": {"command": _py(f"open(r'{log}','a').write('b\\\\n')"), "deps": ["a"]},
        },
    )

    code = run_cli(["--config", str(cfg), "run"])
    captured = capsys.readouterr()

    assert code == 0
    assert log.read_text(encoding="utf-8").splitlines() == ["a", "b"]
    assert "OK a" in captured.out
    assert "OK b" in captured.out


def test_run_target_executes_only_subgraph(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "taskforge.json"
    log = tmp_path / "log.txt"

    _write_json_config(
        cfg,
        {
            "a": {"command": _py(f"open(r'{log}','a').write('a\\\\n')")},
            "b": {"command": _py(f"open(r'{log}','a').write('b\\\\n')"), "deps": ["a"]},
            "c": {"command": _py(f"open(r'{log}','a').write('c\\\\n')")},
            "d": {"command": _py(f"open(r'{log}','a').write('d\\\\n')"), "deps": ["b"]},
        },
    )

    code = run_cli(["--config", str(cfg), "run", "d"])
    _ = capsys.readouterr()

    assert code == 0
    assert log.read_text(encoding="utf-8").splitlines() == ["a", "b", "d"]


def test_run_failure_returns_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "taskforge.json"
    _write_json_config(
        cfg,
        {
            "fail": {"command": _py("raise SystemExit(5)")},
        },
    )

    code = run_cli(["--config", str(cfg), "run"])
    out = capsys.readouterr().out

    assert code == 1
    assert "FAIL fail" in out


def test_invalid_config_path_returns_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing.json"

    code = run_cli(["--config", str(missing), "list"])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.err != ""


def test_unknown_target_returns_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "taskforge.json"
    _write_json_config(cfg, {"a": {"command": _py("raise SystemExit(0)")}})

    code = run_cli(["--config", str(cfg), "run", "nope"])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.err != ""
