# Design of Taskforge

This Markdown file is there to write down the mental model of this project before commiting to code.

## Description of the project

Taskforge is a CLI tool that runs task in a simple configuration file. Taskforge figures out the correct order to run everything, makes sure the dependencies run first, stops when something fails, and shows clean logs of what happened.

## Task model

Each task has:

- `id`: string, unique.
- `deps`: array of other task `id`.
- `command`: string to execute via shell.
- `env`: dict of env vars to add/override. (optionnal)
- `working_dir`: string of a path. (optionnal)

A task succeeds if the process exits with code 0, fails otherwise.

No dynamic generation of tasks at runtime.

## Dependencies

A task may only run after all dependencies succeeded.

If a dependency fails:

- The dependant task is skipped.
- The whole `run` exits non-zero.

No cycles allowed. Config is rejected if cycles exists.

## Execution

Sequential mode:

- Execute tasks one-by-one in topological order.

Parallel mode:

- At each "layer" of the topo order, run all tasks whose deps are satisfied concurrently (bounded by workers ?)
- Keeps dependency ordering.
- It should be deterministic: same config + same args -> same execution order of layers and same log ordering.

## CLI

### Run

```bash
taskforge run <task-id> [...]
```

- Accepts one or more target tasks.
- Loads config from a default path (taskforge.yml) or --config.
- Builds graph from all tasks in config, then extracts the subgraph needed for targets.

### List

```bash
taskforge list
```

- Prints all tasks (id + maybe short description)

### Graph

```bash
taskforge graph
```

- Prints a textual representation of the graph.
- Output DOT, but that's extra lol.

## Failure and exit codes

If any tasks fails, taskforge exits with non-zeros.

If config is invalid (parse error, missing fields, duplicate ids, cycles, unknown task refs) -> fail fast with non-zero and a clear message.

In parallel mode, continue running independant tasks even if another branch fails, BUT mark the run overall as failed.

## Logging

Minimal stuctured log :

- Timestamp
- Level (`INFO`, `ERROR`, etc)
- Components (`config`, `graph`, `executor`, `cli`, etc)
- Message

Logs to stdout only (for now).

Executor logs:

- Task start (id)
- Task finish (id, status, duration, exit code)
- Whether it was skipped due to dependency failure (maybe)
