import json
import tomllib
from pathlib import Path
from typing import Any, Mapping

import yaml

from .types import ConfigError, ProjectConfig, TaskConfig, UnsupportedConfigFormatError


def load_project(path: str | Path) -> ProjectConfig:
    pure_path = Path(path).expanduser().resolve()

    if not pure_path.exists():
        raise ConfigError(f"Config file not found: {pure_path}")

    if not pure_path.is_file():
        raise ConfigError(f"Config path is not a file: {pure_path}")

    fmt = _detect_format(pure_path)
    raw_file = _parse_file(pure_path, fmt)
    project = _build_project_config(raw_file)
    return project


def _detect_format(path: Path) -> str:
    fmt = path.suffix
    match fmt:
        case ".yaml" | ".yml":
            return "yaml"
        case ".toml":
            return "toml"
        case ".json":
            return "json"
        case _:
            raise UnsupportedConfigFormatError(
                f"Non supported file extension: {fmt}\n Expected format: .yml/.yaml, .toml, .json"
            )


def _parse_file(path: Path, fmt: str) -> Mapping[str, Any]:
    match fmt:
        case "yaml":
            return _parse_yaml(path)
        case "toml":
            return _parse_toml(path)
        case "json":
            return _parse_json(path)
        case _:
            raise AssertionError("Unreachable")


def _parse_yaml(path: Path) -> Mapping[str, Any]:
    try:
        raw_file = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML") from exc

    if not isinstance(raw_file, Mapping):
        raise ConfigError(
            f"{path}: YAML parsed succesfully but top-level value in not an object: {type(raw_file)}"
        )

    return raw_file


def _parse_toml(path: Path) -> Mapping[str, Any]:
    try:
        raw_file = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML") from exc

    if not isinstance(raw_file, Mapping):
        raise ConfigError(
            f"{path}: TOML parsed succesfully but top-level value in not an object: {type(raw_file)}"
        )

    return raw_file


def _parse_json(path: Path) -> Mapping[str, Any]:
    try:
        raw_file = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON") from exc

    if not isinstance(raw_file, Mapping):
        raise ConfigError(
            f"{path}: JSON parsed succesfully but top-level value in not an object: {type(raw_file)}"
        )

    return raw_file


def _build_project_config(raw: Mapping[str, Any]) -> ProjectConfig:
    tasks = {}

    if not "tasks" in raw:
        raise ConfigError(f"Missing 'tasks' field")

    if not isinstance(raw["tasks"], Mapping):
        raise ConfigError(f"'tasks' must be a mapping, got {type(raw['tasks'])}")

    if len(raw["tasks"]) < 1:
        raise ConfigError(f"There must be at least one task in the config file")

    for task_id, fields in raw["tasks"].items():
        if not isinstance(fields, Mapping):
            raise ConfigError(f"{task_id} must be a mapping")

        if not isinstance(task_id, str):
            raise ConfigError(f"Task id must be a string, got {type(task_id)}")

        task_id_norm = task_id.strip()

        if len(task_id_norm) < 1:
            raise ConfigError(f"A task id can't be empty")

        if task_id_norm in tasks:
            raise ConfigError(f"Duplicate task id after normalization: {task_id_norm}")

        task_config = _build_task_config(task_id_norm, fields)
        tasks[task_id_norm] = task_config

    for task in tasks.values():
        for dep in task.deps:
            if dep not in tasks:
                raise ConfigError(f"Task '{task.id}' has unknown dependency '{dep}'")

    return ProjectConfig(tasks=tasks)


def _build_task_config(task_id: str, fields: Mapping[str, Any]) -> TaskConfig:
    keys = {"command", "deps", "env", "working_dir"}
    deps = []
    seen = set()
    env = {}
    working_dir = None

    for field in fields.keys():
        if field not in keys:
            raise ConfigError(f"{task_id}: Can't process: {field}")

    if not "command" in fields:
        raise ConfigError(f"{task_id}: missing 'command'")

    if not isinstance(fields["command"], str):
        raise ConfigError(f"{task_id}: The command should be a string")

    if len(fields["command"].strip()) < 1:
        raise ConfigError(f"{task_id}: Command missing")

    command = fields["command"].strip()

    if "deps" in fields:
        if not isinstance(fields["deps"], list):
            raise ConfigError(f"{task_id}: Dependencies should be in a list.")

        for item in fields["deps"]:
            if not isinstance(item, str):
                raise ConfigError(
                    f"{task_id}: {item} should be a string in the dependency list"
                )

            dep = item.strip()

            if len(dep) < 1:
                raise ConfigError(f"{task_id}: A dependency is empty")

            if dep == task_id:
                raise ConfigError(f"{task_id}: A task cannot be self dependent")

            # Allows to ignore duplicates dependency
            if dep in seen:
                continue

            deps.append(dep)
            seen.add(dep)

    if "env" in fields:
        if not isinstance(fields["env"], Mapping):
            raise ConfigError(f"{task_id}: Env should be a mapping")

        for key, item in fields["env"].items():
            if not isinstance(key, str):
                raise ConfigError(f"{task_id}: {key} should be a string")

            if len(key.strip()) < 1:
                raise ConfigError(f"{task_id}: A key can't be empty")

            if not isinstance(item, str):
                raise ConfigError(f"{task_id}: {item} should be a string")

            env[key.strip()] = item

    if "working_dir" in fields:
        if not isinstance(fields["working_dir"], str):
            raise ConfigError(f"{task_id}: The working_dir should be a string")

        if len(fields["working_dir"].strip()) < 1:
            raise ConfigError(
                f"{task_id}: Please provide a string or remove this field"
            )

        working_dir = fields["working_dir"].strip()

    return TaskConfig(task_id, command, deps, env, working_dir)
