# Taskforge

Local task runner with explicit dependencies (DAG) and deterministic execution.

## Install (dev)

```bash
git clone https://github.com/ntino67/taskforge
cd taskforge
python -m pip install -e .
```

## Config

Supported formats: YAML (`.yml/.yaml`), TOML (`.toml`), JSON (`.json`)

Example `taskforge.yml`

```yaml
tasks:
  build:
    command: "echo build"
  test:
    command: "echo test"
    deps: ["build"]
```

## Usage

List tasks:

```bash
taskforge list
```

Show dependencies (adjacency list):

```bash
taskforge graph
```

Run all tasks (topological order):

```bash
taskforge run
```

Run a single target and it's dependencies:

```bash
taskforge run test
```

Select config path:

```bash
taskforge --config path/to/taskforge.yaml run
```

Disable fail-fast (continue independent tasks after a failure):

```bash
taskforge run --no-fail-fast
```

You can use `--help` with every commands.

## Exit codes

- `0`: success
- `1`: at least one task failed
- `2`: config/graph/argument error
- `130`: interrupted (Ctrl-C)

## What next ?

The following features are intentionally **out of scope for v0.1.0** and will be developed on separate branches to preserve stability and clean architecture.

### Parallel execution

- Execute independent tasks concurrently
- Bounded worker pool
- Deterministic scheduling (same config → same execution order)
- No async; use threads or processes explicitly

### Multiple targets

- Support `taskforge run <task1> <task2> ...`
- Compute the union of transitive dependencies
- Execute each task at most once
- Deterministic combined order

### Structured logging

- Central `log` module
- Structured messages:
  - timestamp
  - level
  - component (`config`, `graph`, `executor`, `cli`)
- No external logging framework

### Rich output modes

- Optional display of stdout/stderr
- Quiet mode
- Summary-only mode

### Graph output formats

- DOT output for visualization
- Optional ASCII graph

---

Each feature will be added incrementally with:

- explicit interfaces
- test coverage first
- no behavior changes to existing commands
