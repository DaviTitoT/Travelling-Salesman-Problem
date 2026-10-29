import random
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from ktsp.baselines import nearest_neighbor, random_order
from ktsp.distances import build_distance_table
from ktsp.instance import generate_instance
from ktsp.solution import route_cost

spec = spec_from_file_location(
    "experiment_runner", Path(__file__).parents[1] / "experiments" / "run.py"
)
assert spec is not None and spec.loader is not None
run = module_from_spec(spec)
spec.loader.exec_module(run)


def test_experiments_compare_initial_strategies(monkeypatch):
    monkeypatch.setattr(run, "GRID_SIZE", 4)
    monkeypatch.setattr(run, "K_VALUES", (3,))
    monkeypatch.setattr(run, "COOLING_RATES", (0.99,))
    monkeypatch.setattr(run, "SEEDS", range(2))
    monkeypatch.setattr(run, "MAX_ITERATIONS", 10)

    results = run.run_experiments()

    assert set(results.initial_solution) == {"nearest_neighbor", "random"}
    assert len(results) == 4
    assert {"initial_cost", "improvement_over_initial_pct"} <= set(results.columns)

    for seed in range(2):
        table = build_distance_table(generate_instance(4, 4, 3, seed))
        seed_results = results[results.seed == seed].set_index("initial_solution")
        nn_cost = route_cost(nearest_neighbor(table), table)
        random_cost = route_cost(random_order(table, random.Random(seed)), table)

        assert seed_results.loc["nearest_neighbor", "initial_cost"] == nn_cost
        assert seed_results.loc["random", "initial_cost"] == random_cost
        assert (seed_results.improvement_over_initial_pct >= 0).all()
