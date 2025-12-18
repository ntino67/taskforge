from dataclasses import dataclass


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    returncode: int
    stdout: str
    stderr: str
    duration_s: float


@dataclass(frozen=True)
class RunResult:
    order: list[str]
    results: dict[str, TaskResult]
    failed: list[str]
    skipped: list[str]
