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


def sample_instance(graph: nx.Graph, k: int, rng: random.Random) -> Instance:
    """Sorteia a base e os k pontos de entrega entre os vértices de um grafo.

    Args:
        graph: Grafo conexo da cidade.
        k: Quantidade de pontos de entrega.
        rng: Gerador aleatório; a mesma semente sorteia os mesmos pontos.

    Returns:
        A instância, com base e pontos de entrega distintos.

    Raises:
        ValueError: Se o grafo não tiver vértices suficientes para base + k pontos.
    """
    n = graph.number_of_nodes()
    if k < 1 or k + 1 > n:
        raise ValueError(f"k deve estar entre 1 e {n - 1}, recebido {k}")
    base, *deliveries = rng.sample(sorted(graph.nodes), k + 1)
    return Instance(graph=graph, base=base, deliveries=tuple(deliveries))


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
    conexo. A base e os k pontos de entrega são sorteados por ``sample_instance``.

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
    rng = random.Random(seed)

    grid = nx.grid_2d_graph(rows, cols)
    graph = nx.convert_node_labels_to_integers(grid, label_attribute="pos")
    for v, (row, col) in graph.nodes(data="pos"):
        graph.nodes[v]["pos"] = (col, -row)  # linha 0 no topo do desenho
    for u, v in graph.edges:
        graph.edges[u, v]["weight"] = rng.randint(1, max_weight)

    edges = list(graph.edges)
    rng.shuffle(edges)
    for u, v in edges[: int(len(edges) * removal_fraction)]:
        weight = graph.edges[u, v]["weight"]
        graph.remove_edge(u, v)
        if not nx.has_path(graph, u, v):  # a rua era uma ponte: recoloca
            graph.add_edge(u, v, weight=weight)

    return sample_instance(graph, k, rng)
