"""Menores caminhos entre a base e os pontos de entrega.

O grafo não liga todos os pares de pontos, então o custo de ir de um ponto de W
a outro é a distância do menor caminho no grafo. Esses caminhos são calculados
uma única vez (Dijkstra) e reaproveitados pelo Simulated Annealing.
"""

from dataclasses import dataclass

import networkx as nx

from ktsp.instance import Instance


@dataclass(frozen=True)
class DistanceTable:
    """Distâncias e caminhos mínimos entre os pontos de interesse.

    Os pontos são indexados por posição: o índice 0 é a base e os índices
    ``1..k`` são os pontos de W, na ordem de ``Instance.deliveries``.

    Attributes:
        points: Vértices do grafo correspondentes a cada índice.
        matrix: ``matrix[i][j]`` é a menor distância do ponto i ao ponto j.
        paths: ``paths[i][j]`` é o menor caminho (lista de vértices) de i a j.
    """

    points: tuple[int, ...]
    matrix: list[list[float]]
    paths: list[list[list[int]]]

    @property
    def k(self) -> int:
        """Quantidade de pontos de entrega."""
        return len(self.points) - 1


def build_distance_table(instance: Instance) -> DistanceTable:
    """Roda Dijkstra a partir da base e de cada ponto de entrega.

    Args:
        instance: Instância do problema.

    Returns:
        Tabela com distâncias e caminhos entre todos os pares de pontos.
    """
    points = (instance.base, *instance.deliveries)
    matrix: list[list[float]] = []
    paths: list[list[list[int]]] = []
    for source in points:
        dist, path = nx.single_source_dijkstra(instance.graph, source)
        matrix.append([dist[target] for target in points])
        paths.append([path[target] for target in points])
    return DistanceTable(points=points, matrix=matrix, paths=paths)
