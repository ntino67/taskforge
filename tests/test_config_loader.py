# tests/test_config_loader.py
# Assumptions:
# - Your loader is at: taskforge/config/loader.py with load_project()
# - Your exceptions/types are at: taskforge/config/types.py
#
# Adjust imports below if your package/module names differ.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from taskforge.config.loader import load_project
from taskforge.config.types import ConfigError, UnsupportedConfigFormatError


# -------------------------
# Helpers
# -------------------------


def write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path: Path, obj: object) -> Path:
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


# -------------------------
# Basic file/path errors
# -------------------------


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_project(tmp_path / "missing.yaml")


def test_path_is_dir_raises_config_error(tmp_path: Path) -> None:
    d = tmp_path / "dir"
    d.mkdir()
    with pytest.raises(ConfigError):
        load_project(d)


def test_unsupported_extension_raises_unsupported_format(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.txt", "tasks: {}")
    with pytest.raises(UnsupportedConfigFormatError):
        load_project(p)


# -------------------------
# Parse errors are wrapped
# -------------------------


def test_invalid_yaml_is_wrapped_as_config_error(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.yaml", "tasks: [\n")  # invalid
    with pytest.raises(ConfigError):
        load_project(p)


def test_invalid_toml_is_wrapped_as_config_error(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.toml", "tasks = {")  # invalid
    with pytest.raises(ConfigError):
        load_project(p)


def test_invalid_json_is_wrapped_as_config_error(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.json", '{"tasks": ')  # invalid
    with pytest.raises(ConfigError):
        load_project(p)


# -------------------------
# Top-level shape validation
# -------------------------


@pytest.mark.parametrize(
    "ext, content",
    [
        (".yaml", "[]\n"),
        (".yaml", "null\n"),
        (
            ".toml",
            'tasks = "nope"\n',
        ),  # valid TOML but wrong type; your code checks Mapping
        (".json", "[]"),
        (".json", "null"),
    ],
)
def test_top_level_not_mapping_raises(tmp_path: Path, ext: str, content: str) -> None:
    p = write_text(tmp_path / f"config{ext}", content)
    with pytest.raises(ConfigError):
        load_project(p)


def test_missing_tasks_key_raises(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.yaml", "not_tasks: {}\n")
    with pytest.raises(ConfigError):
        load_project(p)


@pytest.mark.parametrize(
    "ext, content",
    [
        (".yaml", "tasks: []\n"),
        (".yaml", "tasks: null\n"),
        (".json", '{"tasks": []}'),
        (".json", '{"tasks": null}'),
        (".toml", 'tasks = "nope"\n'),
        (".toml", "tasks = 123\n"),
    ],
)
def test_tasks_not_mapping_raises(tmp_path: Path, ext: str, content: str) -> None:
    p = write_text(tmp_path / f"config{ext}", content)
    with pytest.raises(ConfigError):
        load_project(p)


@pytest.mark.parametrize(
    "ext, content",
    [
        (".yaml", "tasks: {}\n"),
        (".json", '{"tasks": {}}'),
        (".toml", "[tasks]\n"),  # empty table => mapping with 0 keys
    ],
)
def test_tasks_empty_raises(tmp_path: Path, ext: str, content: str) -> None:
    p = write_text(tmp_path / f"config{ext}", content)
    with pytest.raises(ConfigError):
        load_project(p)


# -------------------------
# Task id validation
# -------------------------


def test_task_id_not_string_yaml_raises(tmp_path: Path) -> None:
    # YAML numeric key => int task_id at runtime
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  1:\n    command: echo hi\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_task_id_empty_after_strip_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        'tasks:\n  "   ":\n    command: echo hi\n',
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_duplicate_task_id_after_normalization_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n"
        "  build:\n"
        "    command: echo 1\n"
        '  " build ":\n'
        "    command: echo 2\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


# -------------------------
# Task fields shape validation
# -------------------------


def test_task_fields_not_mapping_raises(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.yaml", "tasks:\n  build: []\n")
    with pytest.raises(ConfigError):
        load_project(p)


def test_unknown_task_field_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  build:\n    command: echo hi\n    nope: 1\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


# -------------------------
# command validation
# -------------------------


def test_missing_command_raises(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.yaml", "tasks:\n  build:\n    deps: []\n")
    with pytest.raises(ConfigError):
        load_project(p)


def test_command_not_string_raises(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.yaml", "tasks:\n  build:\n    command: 123\n")
    with pytest.raises(ConfigError):
        load_project(p)


def test_command_empty_after_strip_raises(tmp_path: Path) -> None:
    p = write_text(tmp_path / "config.yaml", 'tasks:\n  build:\n    command: "   "\n')
    with pytest.raises(ConfigError):
        load_project(p)


# -------------------------
# deps validation
# -------------------------


def test_deps_not_list_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  build:\n    command: echo hi\n    deps: no\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_deps_contains_non_string_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  build:\n    command: echo hi\n    deps: [1]\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_deps_contains_empty_string_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        'tasks:\n  build:\n    command: echo hi\n    deps: ["   "]\n',
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_deps_self_dependency_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  build:\n    command: echo hi\n    deps: [build]\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_unknown_dependency_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n" "  a:\n" "    command: echo a\n" "    deps: [b]\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_duplicate_deps_are_ignored_and_preserve_order(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n"
        "  a:\n"
        "    command: echo a\n"
        '    deps: [b, " b ", c, b]\n'
        "  b:\n"
        "    command: echo b\n"
        "  c:\n"
        "    command: echo c\n",
    )
    proj = load_project(p)
    assert proj.tasks["a"].deps == ["b", "c"]


# -------------------------
# env validation
# -------------------------


def test_env_not_mapping_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  a:\n    command: echo a\n    env: []\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_env_key_not_string_yaml_raises(tmp_path: Path) -> None:
    # YAML allows non-string keys in mappings
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  a:\n    command: echo a\n    env:\n      1: x\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_env_key_empty_after_strip_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        'tasks:\n  a:\n    command: echo a\n    env:\n      "   ": x\n',
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_env_value_not_string_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  a:\n    command: echo a\n    env:\n      KEY: 1\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_env_key_is_stripped_value_preserved(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        'tasks:\n  a:\n    command: echo a\n    env:\n      " KEY ": "  v  "\n',
    )
    proj = load_project(p)
    assert proj.tasks["a"].env == {"KEY": "  v  "}


# -------------------------
# working_dir validation
# -------------------------


def test_working_dir_not_string_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n  a:\n    command: echo a\n    working_dir: 1\n",
    )
    with pytest.raises(ConfigError):
        load_project(p)


def test_working_dir_empty_string_raises(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        'tasks:\n  a:\n    command: echo a\n    working_dir: "   "\n',
    )
    with pytest.raises(ConfigError):
        load_project(p)


# -------------------------
# Happy paths (all formats)
# -------------------------


def test_valid_yaml_loads(tmp_path: Path) -> None:
    p = write_text(
        tmp_path / "config.yaml",
        "tasks:\n"
        "  build:\n"
        "    command: echo build\n"
        "    deps: [test]\n"
        "    env:\n"
        "      KEY: value\n"
        "  test:\n"
        "    command: echo test\n",
    )
    proj = load_project(p)
    assert set(proj.tasks.keys()) == {"build", "test"}
    assert proj.tasks["build"].deps == ["test"]
    assert proj.tasks["build"].env == {"KEY": "value"}


def test_valid_json_loads(tmp_path: Path) -> None:
    obj = {
        "tasks": {
            "a": {"command": "echo a"},
            "b": {"command": "echo b", "deps": ["a"]},
        }
    }
    p = write_json(tmp_path / "config.json", obj)
    proj = load_project(p)
    assert set(proj.tasks.keys()) == {"a", "b"}
    assert proj.tasks["b"].deps == ["a"]


def test_valid_toml_loads(tmp_path: Path) -> None:
    # TOML tables: [tasks.<id>]
    p = write_text(
        tmp_path / "config.toml",
        "[tasks.a]\n"
        'command = "echo a"\n'
        "\n"
        "[tasks.b]\n"
        'command = "echo b"\n'
        'deps = ["a"]\n',
    )
    proj = load_project(p)
    assert set(proj.tasks.keys()) == {"a", "b"}
    assert proj.tasks["b"].deps == ["a"]
