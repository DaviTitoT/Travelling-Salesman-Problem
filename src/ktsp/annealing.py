"""Simulated Annealing para o k-TSP.

O algoritmo é um gerador: emite um ``Step`` por iteração. A aplicação usa todos
os passos para animar a busca; os experimentos usam só o último.
"""

import math
import random
from collections.abc import Iterator
from dataclasses import dataclass

from ktsp.distances import DistanceTable
from ktsp.solution import Order, route_cost


@dataclass(frozen=True)
class AnnealingParams:
    """Parâmetros do Simulated Annealing.

    Attributes:
        initial_temperature: Temperatura inicial T0.
        cooling_rate: Fator alfa do resfriamento geométrico (T <- alfa * T).
        max_iterations: Limite de iterações.
        min_temperature: A busca para quando T fica abaixo deste valor.
    """

    initial_temperature: float = 100.0
    cooling_rate: float = 0.995
    max_iterations: int = 5000
    min_temperature: float = 1e-3

    def __post_init__(self) -> None:
        """Rejeita parâmetros que tornariam a busca inválida."""
        if self.initial_temperature <= 0 or self.min_temperature <= 0:
            raise ValueError("as temperaturas devem ser positivas")
        if not 0 < self.cooling_rate < 1:
            raise ValueError("a taxa de resfriamento deve estar entre 0 e 1")
        if self.max_iterations < 0:
            raise ValueError("o máximo de iterações não pode ser negativo")


@dataclass(frozen=True)
class Step:
    """Estado da busca ao fim de uma iteração.

    Attributes:
        iteration: Número da iteração (0 é a solução inicial).
        temperature: Temperatura usada nesta iteração.
        current_order: Solução corrente após a decisão de aceitação.
        current_cost: Custo da solução corrente.
        best_order: Melhor solução encontrada até aqui.
        best_cost: Custo da melhor solução.
        worse: O vizinho sorteado era pior que a solução corrente.
        accepted: O vizinho sorteado foi aceito.
    """

    iteration: int
    temperature: float
    current_order: Order
    current_cost: float
    best_order: Order
    best_cost: float
    worse: bool
    accepted: bool


def two_opt_neighbor(order: Order, rng: random.Random) -> Order:
    """Inverte um trecho aleatório da ordem de visita (movimento 2-opt).

    Args:
        order: Ordem atual, com pelo menos 2 pontos.
        rng: Gerador de números aleatórios.

    Returns:
        Nova ordem com o trecho ``order[i..j]`` invertido.
    """
    i, j = sorted(rng.sample(range(len(order)), 2))
    return order[:i] + order[i : j + 1][::-1] + order[j + 1 :]


def anneal(
    table: DistanceTable,
    initial_order: Order,
    params: AnnealingParams,
    rng: random.Random,
) -> Iterator[Step]:
    """Executa o Simulated Annealing a partir de uma ordem inicial.

    Um vizinho melhor é sempre aceito; um pior (diferença ``delta`` > 0) é
    aceito com probabilidade ``exp(-delta / T)``, o que permite escapar de
    mínimos locais enquanto a temperatura está alta.

    Args:
        table: Tabela de distâncias mínimas.
        initial_order: Permutação inicial dos índices ``1..k``.
        params: Parâmetros do algoritmo.
        rng: Gerador de números aleatórios.

    Yields:
        O estado inicial (iteração 0) e depois um estado por iteração.
    """
    current = best = tuple(initial_order)
    current_cost = best_cost = route_cost(current, table)
    temperature = params.initial_temperature
    yield Step(0, temperature, current, current_cost, best, best_cost, False, False)
    if len(current) < 2:  # com um único ponto só existe uma rota
        return

    for iteration in range(1, params.max_iterations + 1):
        if temperature < params.min_temperature:
            return
        candidate = two_opt_neighbor(current, rng)
        delta = route_cost(candidate, table) - current_cost
        worse = delta > 0
        # shortcut: math.exp vem da libm do sistema e pode diferir em 1 ulp entre
        # plataformas; só mudaria a decisão num empate de ~1e-16, sem efeito prático
        accepted = not worse or rng.random() < math.exp(-delta / temperature)
        if accepted:
            current, current_cost = candidate, current_cost + delta
            if current_cost < best_cost:
                best, best_cost = current, current_cost
        yield Step(
            iteration,
            temperature,
            current,
            current_cost,
            best,
            best_cost,
            worse,
            accepted,
        )
        temperature *= params.cooling_rate
