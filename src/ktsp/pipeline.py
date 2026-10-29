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
from ktsp.instance import Instance, generate_instance, sample_instance
from ktsp.solution import Order
from ktsp.street_map import load_street_map

CITIES = ("grid", "ibirapuita")  # grade sintética ou o bairro real
DEFAULT_CITY = "grid"
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


def build_instance(city: str, size: int, k: int, seed: int) -> Instance:
    """Monta a instância na cidade pedida.

    Args:
        city: ``"grid"`` (grade sintética ``size`` x ``size``) ou
            ``"ibirapuita"`` (bairro real, que ignora ``size``).
        size: Lado da grade.
        k: Quantidade de pontos de entrega.
        seed: Semente da cidade. Na grade, define ruas, pesos, base e entregas;
            no bairro real, só a base e as entregas.

    Returns:
        A instância.

    Raises:
        ValueError: Se a cidade não existir ou k não couber nela.
    """
    if city == "grid":
        return generate_instance(size, size, k, seed)
    if city == "ibirapuita":
        return sample_instance(load_street_map().graph, k, random.Random(seed))
    raise ValueError(f"Cidade desconhecida: {city!r}. Use uma de {CITIES}.")


def solve(
    size: int = DEFAULT_SIZE,
    k: int = DEFAULT_K,
    seed: int = DEFAULT_SEED,
    sa_seed: int = DEFAULT_SA_SEED,
    params: AnnealingParams = AnnealingParams(),  # noqa: B008 (imutável)
    city: str = DEFAULT_CITY,
    base: int | None = None,
) -> Run:
    """Monta a cidade e roda o SA a partir do vizinho mais próximo.

    Args:
        size: Lado da grade (só na grade sintética).
        k: Quantidade de pontos de entrega.
        seed: Semente da cidade (ver ``build_instance``).
        sa_seed: Semente das escolhas aleatórias do SA.
        params: Parâmetros do SA.
        city: ``"grid"`` ou ``"ibirapuita"``.
        base: Vértice que será usado como base; por padrão, mantém a base gerada.

    Returns:
        A execução completa, com o histórico de passos.
    """
    instance = build_instance(city, size, k, seed)
    if base is not None:
        if base not in instance.graph:
            if city == "grid":
                raise ValueError(
                    f"A base {base} não existe na grade de tamanho {size}."
                )
            raise ValueError(f"A base {base} não existe na cidade {city!r}.")
        deliveries = tuple(
            instance.base if delivery == base else delivery
            for delivery in instance.deliveries
        )
        instance = Instance(graph=instance.graph, base=base, deliveries=deliveries)
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
