import random
from itertools import pairwise

import networkx as nx
import pytest

from ktsp.annealing import AnnealingParams, anneal
from ktsp.baselines import brute_force, nearest_neighbor
from ktsp.distances import build_distance_table
from ktsp.instance import generate_instance
from ktsp.solution import Route


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
