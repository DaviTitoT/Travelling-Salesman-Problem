from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location("api", Path(__file__).parents[1] / "app" / "api.py")
assert spec is not None and spec.loader is not None
api = module_from_spec(spec)
spec.loader.exec_module(api)


def test_solve_compares_selected_and_random_bases():
    result = api.solve(
        {
            "size": 4,
            "k": 4,
            "seed": 42,
            "routeBase": "random",
            "randomSeed": 1234,
            "maxIterations": 10,
        }
    )

    comparison = {item["strategy"]: item for item in result["comparisons"]}
    assert set(comparison) == {"selected", "random"}
    assert result["routeBase"] == "random"
    assert result["initialCost"] == comparison["random"]["initialCost"]
    assert result["bestCost"] == comparison["random"]["bestCost"]
    assert all(item["bestCost"] <= item["initialCost"] for item in comparison.values())
    assert comparison["selected"]["base"] != comparison["random"]["base"]
    assert set(comparison["selected"]["initialVisits"]) == set(
        comparison["random"]["initialVisits"]
    )


def test_solve_comparison_is_reproducible():
    payload = {
        "size": 4,
        "k": 4,
        "seed": 42,
        "randomSeed": 1234,
        "maxIterations": 10,
    }

    first = api.solve(payload)
    second = api.solve(payload)

    assert first["comparisons"] == second["comparisons"]


def test_solve_uses_selected_base_and_keeps_deliveries_distinct():
    base = [2, 1]
    result = api.solve(
        {
            "size": 4,
            "k": 4,
            "seed": 42,
            "randomSeed": 1234,
            "base": base,
            "maxIterations": 10,
        }
    )
    assert result["base"] == base
    assert base not in result["deliveries"]
    comparison = {item["strategy"]: item for item in result["comparisons"]}
    assert comparison["selected"]["base"] == base
    assert comparison["random"]["base"] != base
    assert all(
        item["bestVertexPath"][0] == item["baseNode"]
        and item["bestVertexPath"][-1] == item["baseNode"]
        for item in result["comparisons"]
    )


def test_solve_rejects_base_outside_grid():
    import pytest

    with pytest.raises(ValueError, match="dentro da grade"):
        api.solve({"size": 4, "k": 3, "base": [4, 1]})


def test_solve_requires_room_for_two_distinct_bases():
    import pytest

    with pytest.raises(ValueError, match="duas posições"):
        api.solve({"size": 4, "k": 15})


def test_random_seed_is_generated_and_can_reproduce_random_base():
    payload = {"size": 4, "k": 4, "seed": 42, "maxIterations": 10}
    first = api.solve(payload)
    replay = api.solve({**payload, "randomSeed": first["randomSeed"]})

    assert isinstance(first["randomSeed"], int)
    comparison = {item["strategy"]: item for item in first["comparisons"]}
    assert comparison["random"]["base"] != comparison["selected"]["base"]
    assert first["comparisons"] == replay["comparisons"]
