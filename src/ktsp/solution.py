"""Representação da solução: ordem de visita, caminho completo e distância.

Uma solução é uma permutação dos índices ``1..k`` da ``DistanceTable``. A rota
implícita é ``base -> pontos na ordem -> base``.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from ktsp.distances import DistanceTable

Order = tuple[int, ...]


def route_cost(order: Sequence[int], table: DistanceTable) -> float:
    """Distância total da rota que visita os pontos na ordem dada.

    Args:
        order: Permutação dos índices ``1..k``.
        table: Tabela de distâncias mínimas.

    Returns:
        Soma das distâncias base -> ... -> base.
    """
    stops = (0, *order, 0)
    return sum(table.matrix[a][b] for a, b in pairwise(stops))


@dataclass(frozen=True)
class Route:
    """Resposta entregue ao entregador.

    Attributes:
        order: Permutação dos índices ``1..k`` da tabela.
        visits: Vértices de W na ordem de visita.
        path: Caminho completo, vértice a vértice, saindo e voltando à base.
        cost: Distância total percorrida.
    """

    order: Order
    visits: tuple[int, ...]
    path: tuple[int, ...]
    cost: float

    @classmethod
    def from_order(cls, order: Sequence[int], table: DistanceTable) -> "Route":
        """Expande uma ordem de visita no caminho completo pelo grafo."""
        stops = (0, *order, 0)
        path = [table.points[0]]
        for a, b in pairwise(stops):
            path.extend(table.paths[a][b][1:])  # [1:] evita repetir o vértice de junção
        return cls(
            order=tuple(order),
            visits=tuple(table.points[i] for i in order),
            path=tuple(path),
            cost=route_cost(order, table),
        )
