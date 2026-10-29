import importlib.util
from itertools import pairwise
from pathlib import Path

import pytest

# app/ não é um pacote: carrega a API pelo caminho.
_spec = importlib.util.spec_from_file_location(
    "app_api", Path(__file__).parents[1] / "app" / "api.py"
)
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)


@pytest.mark.parametrize("city", ["grid", "ibirapuita"])
def test_solve_returns_drawable_route(city):
    result = api.solve({"city": city, "k": 6, "maxIterations": 500})
    positions, edges = result["positions"], {tuple(e) for e in result["edges"]}
    for step in (result["steps"][0], result["steps"][-1]):
        path = step["bestPath"]
        assert path[0] == path[-1] == result["base"]
        # toda rota desenhada anda só por ruas que existem no mapa
        assert all((u, v) in edges or (v, u) in edges for u, v in pairwise(path))
    assert all(len(positions[v]) == 2 for v in result["bestVertexPath"])
    assert result["geographic"] == (city == "ibirapuita")


def test_real_map_positions_are_lat_lng_in_alegrete():
    result = api.solve({"city": "ibirapuita", "k": 3, "maxIterations": 50})
    lat, lng = result["positions"][result["base"]]
    assert -29.80 < lat < -29.77 and -55.79 < lng < -55.76
    assert result["unit"] == "m" and result["boundary"]


@pytest.mark.parametrize(
    "payload",
    [{"city": "atlantida"}, {"city": "grid", "size": 4, "k": 20}, {"k": 41}],
)
def test_invalid_payload_raises(payload):
    with pytest.raises(ValueError):
        api.solve(payload)
