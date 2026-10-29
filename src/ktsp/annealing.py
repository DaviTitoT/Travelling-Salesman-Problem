"""Simulated Annealing para o k-TSP.

O algoritmo é um gerador: emite um ``Step`` por iteração. A aplicação usa todos
os passos para animar a busca; os experimentos usam só o último. Toda execução
avalia exatamente ``max_iterations`` vizinhos, para que execuções com parâmetros
diferentes sejam comparadas com o mesmo orçamento.

Com ``tabu_tenure > 0`` a busca vira um híbrido SA + Tabu: os últimos movimentos
avaliados ficam proibidos e não gastam orçamento, o que evita reavaliar os mesmos
vizinhos quando a busca está parada num ótimo local. Com ``tabu_tenure = 0`` o
algoritmo é o SA puro.
"""

import math
import random
from collections import deque
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
        max_iterations: Orçamento: quantidade de vizinhos avaliados.
        tabu_tenure: Tamanho da lista tabu (movimentos recentes proibidos);
            0 desliga a lista e mantém o SA puro.
    """

    initial_temperature: float = 100.0
    cooling_rate: float = 0.995
    max_iterations: int = 5000
    tabu_tenure: int = 0

    def __post_init__(self) -> None:
        """Rejeita parâmetros que tornariam a busca inválida."""
        if self.initial_temperature <= 0:
            raise ValueError("a temperatura inicial deve ser positiva")
        if not 0 < self.cooling_rate < 1:
            raise ValueError("a taxa de resfriamento deve estar entre 0 e 1")
        if self.max_iterations < 0:
            raise ValueError("o máximo de iterações não pode ser negativo")
        if self.tabu_tenure < 0:
            raise ValueError("o tamanho da lista tabu não pode ser negativo")


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


Move = tuple[int, int]


def random_move(size: int, rng: random.Random) -> Move:
    """Sorteia um movimento 2-opt: as posições ``i < j`` do trecho a inverter."""
    i, j = sorted(rng.sample(range(size), 2))
    return i, j


def reverse_segment(order: Order, move: Move) -> Order:
    """Aplica o movimento 2-opt: inverte o trecho ``order[i..j]``."""
    i, j = move
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

    # Deixa ao menos um movimento livre, para o sorteio abaixo sempre terminar.
    moves = len(current) * (len(current) - 1) // 2
    tabu: deque[Move] = deque(maxlen=min(params.tabu_tenure, moves - 1))
    for iteration in range(1, params.max_iterations + 1):
        move = random_move(len(current), rng)
        while move in tabu:  # movimento proibido: sorteia outro sem avaliá-lo
            move = random_move(len(current), rng)
        tabu.append(move)
        candidate = reverse_segment(current, move)
        delta = route_cost(candidate, table) - current_cost
        worse = delta > 0
        # shortcut: math.exp vem da libm do sistema e pode diferir em 1 ulp entre
        # plataformas; só mudaria a decisão num empate de ~1e-16, sem efeito prático
        # com T = 0 (underflow após muitas iterações) nenhuma piora é aceita
        accepted = not worse or (
            temperature > 0 and rng.random() < math.exp(-delta / temperature)
        )
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
