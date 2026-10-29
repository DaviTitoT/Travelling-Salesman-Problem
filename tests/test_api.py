import importlib.util
from itertools import pairwise
from pathlib import Path

import pytest

from ktsp import pipeline

# app/ não é um pacote: carrega a API pelo caminho.
_spec = importlib.util.spec_from_file_location(
    "app_api", Path(__file__).parents[1] / "app" / "api.py"
)
assert _spec is not None and _spec.loader is not None
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)


@pytest.mark.parametrize("city", ["grid", "ibirapuita"])
def test_solve_returns_drawable_vertex_paths(city):
    result = api.solve(
        {
            "city": city,
            "k": 6,
            "randomSeed": 1234,
            "maxIterations": 500,
        }
    )
    positions = result["positions"]
    edges = {tuple(edge) for edge in result["edges"]}
    route_base = result["displayBase"]

    for step in (result["steps"][0], result["steps"][-1]):
        path = step["bestPath"]
        assert path[0] == path[-1] == route_base
        # Toda rota desenhada usa somente ruas existentes no grafo.
        assert all((u, v) in edges or (v, u) in edges for u, v in pairwise(path))
    assert all(len(positions[vertex]) == 2 for vertex in result["bestVertexPath"])
    assert result["geographic"] == (city == "ibirapuita")


@pytest.mark.parametrize("city", ["grid", "ibirapuita"])
def test_selected_base_and_real_map_contract_work_together(city):
    generated = pipeline.build_instance(city, size=4, k=3, seed=42)
    selected_base = generated.deliveries[0]
    result = api.solve(
        {
            "city": city,
            "size": 4,
            "k": 3,
            "seed": 42,
            "base": selected_base,
            "routeBase": "random",
            "randomSeed": 1234,
            "maxIterations": 50,
        }
    )

    comparisons = {entry["strategy"]: entry for entry in result["comparisons"]}
    assert result["base"] == selected_base
    assert result["displayBase"] == comparisons["random"]["base"]
    assert comparisons["selected"]["base"] == selected_base
    assert comparisons["selected"]["base"] != comparisons["random"]["base"]
    assert selected_base not in result["deliveries"]
    assert generated.base in result["deliveries"]
    assert set(comparisons["selected"]["initialVisits"]) == set(
        comparisons["random"]["initialVisits"]
    )

    # IDs remain the route/edge values; positions are indexed by ID.
    positions = result["positions"]
    edges = {tuple(edge) for edge in result["edges"]}
    assert len(positions) == generated.graph.number_of_nodes()
    assert all(0 <= vertex < len(positions) for edge in edges for vertex in edge)
    for step in (result["steps"][0], result["steps"][-1]):
        path = step["bestPath"]
        assert path[0] == path[-1] == result["displayBase"]
        assert all((u, v) in edges or (v, u) in edges for u, v in pairwise(path))

    if city == "ibirapuita":
        lat, lng = positions[selected_base]
        assert -29.80 < lat < -29.77 and -55.79 < lng < -55.76
        assert result["unit"] == "m" and result["boundary"]
    else:
        assert not result["boundary"]
        assert result["unit"] == "unidades"


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


def test_generated_random_seed_reproduces_random_base():
    payload = {"size": 4, "k": 4, "seed": 42, "maxIterations": 10}
    first = api.solve(payload)
    replay = api.solve({**payload, "randomSeed": first["randomSeed"]})

    assert isinstance(first["randomSeed"], int)
    assert first["comparisons"] == replay["comparisons"]


@pytest.mark.parametrize(
    "payload",
    [
        {"city": "atlantida"},
        {"city": "grid", "size": 4, "k": 15},
        {"city": "grid", "base": 999},
        {"routeBase": "other"},
        {"k": 41},
    ],
)
def test_invalid_payload_raises(payload):
    with pytest.raises(ValueError):
        api.solve(payload)
