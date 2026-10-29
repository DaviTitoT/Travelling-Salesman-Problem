"""Cidade real: grafo de ruas de um bairro, extraído do OpenStreetMap.

O arquivo é gerado por ``scripts/download_street_map.py`` e fica dentro do
pacote. Cada vértice tem ``pos`` = (longitude, latitude) e cada aresta tem
``weight`` = comprimento da rua em metros (inteiro).
"""

import json
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

IBIRAPUITA = Path(__file__).parent / "data" / "ibirapuita.json"

Point = tuple[float, float]


@dataclass(frozen=True)
class StreetMap:
    """Grafo de ruas de um bairro real.

    Attributes:
        name: Nome do lugar.
        graph: Grafo conexo das ruas, com vértices numerados de 0 a n-1.
        boundary: Contorno do bairro em (longitude, latitude); o primeiro ponto
            se repete no fim.
        attribution: Crédito exigido pela licença dos dados.
    """

    name: str
    graph: nx.Graph
    boundary: tuple[Point, ...]
    attribution: str


def load_street_map(path: Path = IBIRAPUITA) -> StreetMap:
    """Lê um mapa salvo pelo script de download.

    Args:
        path: Arquivo JSON do mapa; por padrão, o bairro Ibirapuitã.

    Returns:
        O mapa com o grafo de ruas.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.Graph()
    for vertex, node in enumerate(data["nodes"]):
        graph.add_node(vertex, pos=(node["lon"], node["lat"]))
    for edge in data["edges"]:
        graph.add_edge(edge["u"], edge["v"], weight=edge["weight"])
    return StreetMap(
        name=data["name"],
        graph=graph,
        boundary=tuple((lon, lat) for lon, lat in data["boundary"]),
        attribution=data["attribution"],
    )
