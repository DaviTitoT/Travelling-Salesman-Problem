import random
from itertools import pairwise

import networkx as nx
import pytest

from ktsp.annealing import AnnealingParams, anneal
from ktsp.baselines import brute_force, nearest_neighbor
from ktsp.cli import main
from ktsp.distances import build_distance_table
from ktsp.instance import generate_instance
from ktsp.pipeline import solve
from ktsp.solution import Route
from ktsp.street_map import load_street_map


@pytest.fixture
def instance():
    return generate_instance(rows=6, cols=6, k=7, seed=42)


@pytest.fixture
def table(instance):
    return build_distance_table(instance)


def test_generated_instance_is_valid(instance):
    assert nx.is_connected(instance.graph)
    assert len(set(instance.deliveries)) == 7
    assert instance.base not in instance.deliveries


def test_generation_is_reproducible():
    a = generate_instance(5, 5, 4, seed=1)
    b = generate_instance(5, 5, 4, seed=1)
    assert a.deliveries == b.deliveries
    assert sorted(a.graph.edges(data="weight")) == sorted(b.graph.edges(data="weight"))


def test_invalid_k_raises():
    with pytest.raises(ValueError):
        generate_instance(2, 2, 4, seed=0)


def test_route_satisfies_constraints(instance, table):
    route = Route.from_order(nearest_neighbor(table), table)
    assert sorted(route.visits) == sorted(instance.deliveries)
    assert route.path[0] == route.path[-1] == instance.base
    assert all(instance.graph.has_edge(u, v) for u, v in pairwise(route.path))
    walked = sum(instance.graph.edges[u, v]["weight"] for u, v in pairwise(route.path))
    assert walked == route.cost


def test_annealing_reaches_optimum_on_small_instance(table):
    params = AnnealingParams(initial_temperature=50, cooling_rate=0.995)
    steps = list(anneal(table, nearest_neighbor(table), params, random.Random(0)))
    assert all(a.best_cost >= b.best_cost for a, b in pairwise(steps))
    optimum = Route.from_order(brute_force(table), table).cost
    assert steps[-1].best_cost == optimum


def test_annealing_with_single_delivery():
    table = build_distance_table(generate_instance(3, 3, 1, seed=0))
    steps = list(anneal(table, (1,), AnnealingParams(), random.Random(0)))
    assert len(steps) == 1


def test_same_parameters_give_identical_runs():
    a, b = solve(), solve()
    assert a.steps == b.steps
    assert sorted(a.instance.graph.edges(data="weight")) == sorted(
        b.instance.graph.edges(data="weight")
    )


def test_default_run_matches_reference_values():
    # Valores gravados em Python 3.12; se mudarem, os resultados deixaram de ser
    # reproduzíveis entre máquinas (versão do Python, networkx ou do algoritmo).
    run = solve()
    last = run.steps[-1]
    assert run.instance.base == 43
    assert run.instance.deliveries == (21, 72, 131, 85, 23, 60, 79, 57, 50, 37)
    assert len(run.instance.graph.edges) == 189
    assert (last.iteration, last.best_cost) == (5000, 273)
    assert last.best_order == (1, 5, 8, 3, 4, 2, 6, 10, 9, 7)


def test_street_map_is_valid():
    street_map = load_street_map()
    graph = street_map.graph
    assert nx.is_connected(graph)
    assert all(weight >= 1 for *_, weight in graph.edges(data="weight"))
    assert all(  # todos os vértices ficam em Alegrete-RS
        -55.79 < lon < -55.76 and -29.80 < lat < -29.77
        for _, (lon, lat) in graph.nodes(data="pos")
    )
    assert street_map.boundary[0] == street_map.boundary[-1]


def test_route_on_street_map_satisfies_constraints():
    run = solve(city="ibirapuita", k=7)
    graph = run.instance.graph
    route = Route.from_order(run.steps[-1].best_order, run.table)
    assert sorted(route.visits) == sorted(run.instance.deliveries)
    assert route.path[0] == route.path[-1] == run.instance.base
    assert all(graph.has_edge(u, v) for u, v in pairwise(route.path))
    walked = sum(graph.edges[u, v]["weight"] for u, v in pairwise(route.path))
    assert walked == route.cost


def test_street_map_run_matches_reference_values():
    # Como na grade: se mudar, o arquivo do mapa ou o sorteio deixou de ser o mesmo.
    run = solve(city="ibirapuita")
    last = run.steps[-1]
    assert run.instance.base == 81
    assert run.instance.deliveries == (14, 3, 94, 35, 31, 28, 17, 13, 86, 114)
    assert (last.iteration, last.best_cost) == (5000, 3696)
    assert last.best_order == (9, 5, 10, 2, 1, 7, 3, 4, 8, 6)


def test_unknown_city_raises():
    with pytest.raises(ValueError):
        solve(city="atlantida")


def test_sa_seed_is_independent_from_city_seed():
    a, b = solve(sa_seed=0), solve(sa_seed=1)
    assert a.instance.deliveries == b.instance.deliveries
    assert a.steps != b.steps


@pytest.mark.parametrize(
    "kwargs",
    [{"initial_temperature": 0}, {"cooling_rate": 1}, {"max_iterations": -1}],
)
def test_invalid_annealing_params_raise(kwargs):
    with pytest.raises(ValueError):
        AnnealingParams(**kwargs)


def test_cli_prints_reproducible_command(capsys):
    main(["--k", "4", "--seed", "7"])
    first = capsys.readouterr().out
    main(["--k", "4", "--seed", "7"])
    assert capsys.readouterr().out == first
    assert "--sa-seed 0" in first and "Distância total (SA)" in first


@pytest.mark.parametrize("alpha", [0.5, 0.99, 0.999])
def test_annealing_spends_the_whole_budget(table, alpha):
    # alpha = 0.5 leva T a 0 por underflow; a busca deve continuar sem erro
    params = AnnealingParams(cooling_rate=alpha, max_iterations=3000)
    steps = list(anneal(table, nearest_neighbor(table), params, random.Random(0)))
    assert steps[-1].iteration == 3000


def test_tabu_hybrid_spends_budget_and_keeps_routes_valid(instance, table):
    params = AnnealingParams(max_iterations=2000, tabu_tenure=10)
    steps = list(anneal(table, nearest_neighbor(table), params, random.Random(0)))
    assert steps[-1].iteration == 2000
    route = Route.from_order(steps[-1].best_order, table)
    assert sorted(route.visits) == sorted(instance.deliveries)
    assert all(a.best_cost >= b.best_cost for a, b in pairwise(steps))


def test_tabu_tenure_larger_than_neighborhood_still_terminates():
    table = build_distance_table(generate_instance(3, 3, 3, seed=0))
    params = AnnealingParams(max_iterations=50, tabu_tenure=100)
    steps = list(anneal(table, (1, 2, 3), params, random.Random(0)))
    assert steps[-1].iteration == 50


def test_tabu_hybrid_differs_from_plain_sa(table):
    plain = list(
        anneal(table, nearest_neighbor(table), AnnealingParams(), random.Random(0))
    )
    hybrid_params = AnnealingParams(tabu_tenure=10)
    hybrid = list(
        anneal(table, nearest_neighbor(table), hybrid_params, random.Random(0))
    )
    assert plain != hybrid
