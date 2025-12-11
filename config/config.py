from dataclasses import dataclass


@dataclass
class TaskConfig:
    id: str
    command: str
    deps: list[str]
    env: dict[str, str]
    working_dir: str | None


@dataclass
class ProjectConfig:
    tasks: dict[str, TaskConfig]

    def __iter__(self):
        for tasks_id in sorted(self.tasks):
            yield self.tasks[tasks_id]

    def __len__(self):
        return len(self.tasks)

    def has_task(self, id: str) -> bool:
        return True if id in self.tasks else False

    def get_task(self, id: str) -> TaskConfig:
        if not self.has_task(id):
            raise KeyError(id)

        return self.tasks[id]

    def tasks_ids(self) -> list[str]:
        return sorted(self.tasks.keys())


class ConfigError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class UnsupportedConfigFormatError(ConfigError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
