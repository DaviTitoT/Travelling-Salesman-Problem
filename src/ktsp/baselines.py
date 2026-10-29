"""Soluções de referência para comparar com o Simulated Annealing."""

import random
from itertools import permutations

from ktsp.distances import DistanceTable
from ktsp.solution import Order, route_cost

MAX_BRUTE_FORCE_K = 8


def nearest_neighbor(table: DistanceTable) -> Order:
    """Heurística gulosa: sempre vai ao ponto não visitado mais próximo.

    Também serve como solução inicial do Simulated Annealing.

    Args:
        table: Tabela de distâncias mínimas.

    Returns:
        Ordem de visita construída gulosamente a partir da base.
    """
    remaining = set(range(1, table.k + 1))
    order: list[int] = []
    current = 0
    while remaining:
        current = min(remaining, key=lambda p: (table.matrix[current][p], p))
        order.append(current)
        remaining.remove(current)
    return tuple(order)


def random_order(table: DistanceTable, rng: random.Random) -> Order:
    """Gera uma ordem aleatória dos pontos de entrega.

    Args:
        table: Tabela de distâncias mínimas.
        rng: Gerador de números aleatórios.

    Returns:
        Permutação aleatória dos índices ``1..k``.
    """
    return tuple(rng.sample(range(1, table.k + 1), table.k))


def brute_force(table: DistanceTable) -> Order:
    """Ótimo exato por enumeração de todas as k! ordens.

    Args:
        table: Tabela de distâncias mínimas.

    Returns:
        Ordem de menor distância total.

    Raises:
        ValueError: Se k passar de ``MAX_BRUTE_FORCE_K`` (tempo proibitivo).
    """
    if table.k > MAX_BRUTE_FORCE_K:
        raise ValueError(f"força bruta limitada a k <= {MAX_BRUTE_FORCE_K}")
    return min(permutations(range(1, table.k + 1)), key=lambda o: route_cost(o, table))
