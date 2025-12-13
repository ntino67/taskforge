class GraphError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class CycleError(GraphError):
    def __init__(self, cycle: list[str]):
        super().__init__("Cycle detected: " + "-> ".join(cycle))
        self.cycle = cycle
