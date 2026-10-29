"""Execução completa: gera a cidade, calcula distâncias e roda o SA.

É o único caminho usado pela CLI e pela API, para que os mesmos parâmetros
produzam exatamente o mesmo resultado em qualquer interface. Toda a
aleatoriedade vem de duas sementes explícitas: ``seed`` (cidade) e
``sa_seed`` (Simulated Annealing).
"""

import random
from dataclasses import dataclass

from ktsp.annealing import AnnealingParams, Step, anneal
from ktsp.baselines import nearest_neighbor
from ktsp.distances import DistanceTable, build_distance_table
from ktsp.instance import Instance, generate_instance
from ktsp.solution import Order

DEFAULT_SIZE = 12
DEFAULT_K = 10
DEFAULT_SEED = 42
DEFAULT_SA_SEED = 0


@dataclass(frozen=True)
class Run:
    """Resultado de uma execução.

    Attributes:
        instance: Cidade gerada.
        table: Distâncias mínimas entre base e entregas.
        initial: Solução inicial (vizinho mais próximo).
        steps: Histórico do SA; o último passo contém a melhor rota.
    """

    instance: Instance
    table: DistanceTable
    initial: Order
    steps: list[Step]


def solve(
    size: int = DEFAULT_SIZE,
    k: int = DEFAULT_K,
    seed: int = DEFAULT_SEED,
    sa_seed: int = DEFAULT_SA_SEED,
    params: AnnealingParams = AnnealingParams(),  # noqa: B008 (imutável)
) -> Run:
    """Gera a cidade ``size`` x ``size`` e roda o SA a partir do vizinho mais próximo.

    Args:
        size: Lado da grade.
        k: Quantidade de pontos de entrega.
        seed: Semente da cidade (ruas, pesos, base e entregas).
        sa_seed: Semente das escolhas aleatórias do SA.
        params: Parâmetros do SA.

    Returns:
        A execução completa, com o histórico de passos.
    """
    instance = generate_instance(size, size, k, seed)
    return solve_instance(instance, sa_seed, params)


def solve_instance(
    instance: Instance,
    sa_seed: int = DEFAULT_SA_SEED,
    params: AnnealingParams = AnnealingParams(),  # noqa: B008 (imutável)
) -> Run:
    """Executa o SA em uma instância já definida.

    Args:
        instance: Cidade, base e entregas da execução.
        sa_seed: Semente das escolhas aleatórias do SA.
        params: Parâmetros do SA.

    Returns:
        A execução completa, com o histórico de passos.
    """
    table = build_distance_table(instance)
    initial = nearest_neighbor(table)
    steps = list(anneal(table, initial, params, random.Random(sa_seed)))
    return Run(instance, table, initial, steps)
