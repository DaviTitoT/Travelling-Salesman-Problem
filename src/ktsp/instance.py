"""Instância do k-TSP: grafo da cidade, base e pontos de entrega."""

import random
from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class Instance:
    """Entrada do problema recebida pela equipe.

    Attributes:
        graph: Grafo não direcionado e conexo. Arestas têm atributo ``weight``
            (distância da rua) e vértices têm atributo ``pos`` (x, y) para desenho.
        base: Vértice de onde o entregador sai e para onde volta.
        deliveries: Vetor W com os k pontos de entrega a visitar.
    """

    graph: nx.Graph
    base: int
    deliveries: tuple[int, ...]


def generate_instance(
    rows: int,
    cols: int,
    k: int,
    seed: int,
    removal_fraction: float = 0.3,
    max_weight: int = 10,
) -> Instance:
    """Gera uma cidade sintética em grade com ruas removidas e pesos aleatórios.

    Parte de uma grade ``rows`` x ``cols``, sorteia pesos inteiros em
    ``[1, max_weight]`` e remove arestas ao acaso, desde que o grafo continue
    conexo. A base e os k pontos de entrega são vértices distintos sorteados.

    Args:
        rows: Número de linhas da grade.
        cols: Número de colunas da grade.
        k: Quantidade de pontos de entrega.
        seed: Semente que torna a instância reproduzível.
        removal_fraction: Fração das arestas que se tenta remover.
        max_weight: Maior distância possível de uma rua.

    Returns:
        A instância gerada.

    Raises:
        ValueError: Se a grade não tiver vértices suficientes para base + k pontos.
    """
    if k < 1 or k + 1 > rows * cols:
        raise ValueError(f"k deve estar entre 1 e {rows * cols - 1}, recebido {k}")
    rng = random.Random(seed)

    grid = nx.grid_2d_graph(rows, cols)
    graph = nx.convert_node_labels_to_integers(grid, label_attribute="pos")
    for u, v in graph.edges:
        graph.edges[u, v]["weight"] = rng.randint(1, max_weight)

    edges = list(graph.edges)
    rng.shuffle(edges)
    for u, v in edges[: int(len(edges) * removal_fraction)]:
        weight = graph.edges[u, v]["weight"]
        graph.remove_edge(u, v)
        if not nx.has_path(graph, u, v):  # a rua era uma ponte: recoloca
            graph.add_edge(u, v, weight=weight)

    base, *deliveries = rng.sample(sorted(graph.nodes), k + 1)
    return Instance(graph=graph, base=base, deliveries=tuple(deliveries))
