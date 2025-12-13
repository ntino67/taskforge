import pytest

from taskforge.config.types import ProjectConfig, TaskConfig
from taskforge.graph.dag import TaskGraph
from taskforge.graph.types import CycleError


def _proj(spec: dict[str, list[str]]) -> ProjectConfig:
    """
    spec: task_id -> deps list
    """
    tasks: dict[str, TaskConfig] = {}
    for task_id, deps in spec.items():
        tasks[task_id] = TaskConfig(
            id=task_id,
            command=f"echo {task_id}",
            deps=list(deps),
            env={},
            working_dir=None,
        )
    return ProjectConfig(tasks=tasks)


def test_topo_linear_chain():
    project = _proj(
        {
            "A": ["B"],
            "B": ["C"],
            "C": [],
        }
    )
    g = TaskGraph.from_project(project)
    assert g.topo_order() == ["C", "B", "A"]


def test_topo_diamond_is_deterministic():
    project = _proj(
        {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        }
    )
    g = TaskGraph.from_project(project)
    assert g.topo_order() == ["D", "B", "C", "A"]


def test_topo_independent_tasks_are_sorted():
    project = _proj(
        {
            "B": [],
            "A": [],
        }
    )
    g = TaskGraph.from_project(project)
    assert g.topo_order() == ["A", "B"]


def test_topo_dep_input_order_does_not_matter():
    project1 = _proj(
        {
            "A": ["B", "C"],
            "B": [],
            "C": [],
        }
    )
    project2 = _proj(
        {
            "A": ["C", "B"],  # reversed
            "B": [],
            "C": [],
        }
    )
    g1 = TaskGraph.from_project(project1)
    g2 = TaskGraph.from_project(project2)
    assert g1.topo_order() == g2.topo_order() == ["B", "C", "A"]


def test_cycle_detection_two_node_cycle():
    project = _proj(
        {
            "A": ["B"],
            "B": ["A"],
        }
    )
    g = TaskGraph.from_project(project)
    with pytest.raises(CycleError):
        g.topo_order()


def test_subgraph_order_target_includes_only_transitive_deps():
    project = _proj(
        {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        }
    )
    g = TaskGraph.from_project(project)
    assert g.subgraph_order("B") == ["D", "B"]
    assert g.subgraph_order("C") == ["D", "C"]
    assert g.subgraph_order("A") == ["D", "B", "C", "A"]


def test_subgraph_order_leaf_returns_itself():
    project = _proj({"A": []})
    g = TaskGraph.from_project(project)
    assert g.subgraph_order("A") == ["A"]


def test_cycle_error_includes_closed_loop_path():
    project = _proj({"A": ["B"], "B": ["A"]})
    g = TaskGraph.from_project(project)

    with pytest.raises(CycleError) as e:
        g.topo_order()

    cycle = e.value.cycle
    assert len(cycle) >= 3
    assert cycle[0] == cycle[-1]
