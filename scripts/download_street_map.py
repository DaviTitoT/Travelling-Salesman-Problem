"""Baixa do OpenStreetMap o mapa real usado nas instâncias: o bairro Ibirapuitã.

Gera ``src/ktsp/data/ibirapuita.json``, já versionado no repositório: o grafo das
ruas por onde a moto pode passar, recortado pelo limite oficial do bairro, e o
contorno do bairro. Só é preciso rodar de novo para atualizar os dados:
``uv run python scripts/download_street_map.py``.

As contas de distância usam metros na projeção Web Mercator, corrigidos pela
latitude; o arquivo guarda longitude e latitude. O sentido das ruas (mão única)
é ignorado, porque o modelo do enunciado é um grafo não direcionado.

Dados © colaboradores do OpenStreetMap (ODbL).
"""

import json
import math
import urllib.request
from itertools import pairwise
from pathlib import Path

import networkx as nx

RELATION_ID = 7981845  # limite administrativo do bairro Ibirapuitã no OSM
NAME = "Ibirapuitã, Alegrete-RS"
OUTPUT = Path(__file__).parents[1] / "src" / "ktsp" / "data" / "ibirapuita.json"
DRIVABLE = {
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
}
BOUNDARY_TOLERANCE_M = 20  # mantém as ruas que formam a divisa do bairro
SIMPLIFY_TOLERANCE_M = 2  # desvio máximo de um vértice removido por estar alinhado
API = "https://api.openstreetmap.org/api/0.6"
USER_AGENT = "ktsp-trabalho-academico/0.1"
ATTRIBUTION = "© colaboradores do OpenStreetMap"
EARTH_RADIUS = 6_378_137.0  # raio da esfera da projeção Web Mercator (m)

Point = tuple[float, float]


def fetch_elements(query: str) -> list[dict]:
    """Nós, vias e relações devolvidos por uma consulta à API do OpenStreetMap."""
    # a política de uso do OSM pede que o cliente se identifique
    request = urllib.request.Request(
        f"{API}/{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())["elements"]


def web_mercator(lon: float, lat: float) -> Point:
    """Projeta longitude e latitude em metros na projeção Web Mercator."""
    return (
        EARTH_RADIUS * math.radians(lon),
        EARTH_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)),
    )


def boundary_ring(elements: list[dict]) -> list[int]:
    """Encadeia as vias do contorno do bairro num anel fechado de nós.

    Args:
        elements: Resposta de ``relation/<id>/full``: a relação e suas vias.

    Returns:
        Identificadores OSM dos nós do contorno; o primeiro se repete no fim.

    Raises:
        ValueError: Se as vias do contorno não formarem um anel fechado.
    """
    relation = next(e for e in elements if e["type"] == "relation")
    way_nodes = {e["id"]: e["nodes"] for e in elements if e["type"] == "way"}
    pieces = [
        way_nodes[m["ref"]]
        for m in relation["members"]
        if m["type"] == "way" and m["role"] == "outer"
    ]
    ring = pieces.pop()
    while pieces:
        piece = next((p for p in pieces if ring[-1] in (p[0], p[-1])), None)
        if piece is None:
            raise ValueError("o contorno do bairro não forma um anel fechado")
        pieces.remove(piece)
        ring += piece[1:] if piece[0] == ring[-1] else piece[-2::-1]
    if ring[0] != ring[-1]:
        raise ValueError("o contorno do bairro não forma um anel fechado")
    return ring


def contains(polygon: list[Point], point: Point) -> bool:
    """Diz se o ponto está dentro do polígono (algoritmo do raio)."""
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in pairwise(polygon):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def segment_distance(point: Point, a: Point, b: Point) -> float:
    """Distância do ponto ao segmento ab."""
    (px, py), (ax, ay), (bx, by) = point, a, b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else ((px - ax) * dx + (py - ay) * dy) / length2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def street_graph(elements: list[dict], polygon: list[Point], scale: float) -> nx.Graph:
    """Monta o grafo conexo das ruas transitáveis do bairro.

    Uma rua entra no grafo se as duas pontas ficam dentro do contorno ou a até
    ``BOUNDARY_TOLERANCE_M`` dele, para não perder as ruas que formam a divisa.
    Se o recorte separar trechos, fica só a maior componente conexa.

    Args:
        elements: Resposta de ``map``: todos os elementos em volta do bairro.
        polygon: Contorno do bairro, na projeção.
        scale: Metros reais por metro da projeção na latitude do bairro.

    Returns:
        Grafo com nós OSM. Arestas têm ``weight`` (metros); nós têm ``xy`` (na
        projeção) e ``lonlat``.
    """
    lonlat = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}
    xy = {node: web_mercator(*coords) for node, coords in lonlat.items()}
    tolerance = BOUNDARY_TOLERANCE_M / scale

    def in_bairro(node: int) -> bool:
        p = xy[node]
        return contains(polygon, p) or any(
            segment_distance(p, a, b) <= tolerance for a, b in pairwise(polygon)
        )

    graph = nx.Graph()
    for way in elements:
        if way["type"] != "way" or way.get("tags", {}).get("highway") not in DRIVABLE:
            continue
        for u, v in pairwise(way["nodes"]):
            if in_bairro(u) and in_bairro(v):
                graph.add_edge(u, v, weight=math.dist(xy[u], xy[v]) * scale)
                for node in (u, v):
                    graph.nodes[node].update(xy=xy[node], lonlat=lonlat[node])
    return graph.subgraph(max(nx.connected_components(graph), key=len)).copy()


def simplify(graph: nx.Graph, tolerance: float) -> None:
    """Remove os vértices de grau 2 alinhados com os vizinhos.

    No OSM, esses vértices só marcam onde uma via foi dividida (troca de nome,
    faixa de pedestres etc.); não são esquinas. A aresta que os substitui soma
    os comprimentos, então as distâncias não mudam. Vértices em curvas ficam,
    para o desenho seguir a rua.

    Args:
        graph: Grafo de ruas, alterado no lugar.
        tolerance: Distância máxima (na projeção) do vértice à reta entre os
            vizinhos.
    """
    removed = True
    while removed:
        removed = False
        for v in list(graph):
            if graph.degree(v) != 2:
                continue
            a, b = graph.neighbors(v)
            xy = graph.nodes
            if graph.has_edge(a, b) or (
                segment_distance(xy[v]["xy"], xy[a]["xy"], xy[b]["xy"]) > tolerance
            ):
                continue
            weight = graph.edges[a, v]["weight"] + graph.edges[v, b]["weight"]
            graph.remove_node(v)
            graph.add_edge(a, b, weight=weight)
            removed = True


def main() -> None:
    """Baixa o bairro, monta o grafo e grava o JSON."""
    relation = fetch_elements(f"relation/{RELATION_ID}/full.json")
    ring = boundary_ring(relation)
    coords = {e["id"]: (e["lon"], e["lat"]) for e in relation if e["type"] == "node"}
    lons, lats = zip(*(coords[n] for n in ring), strict=True)
    polygon = [web_mercator(*coords[n]) for n in ring]
    # a Web Mercator aumenta as distâncias por 1/cos(latitude)
    scale = math.cos(math.radians(sum(lats) / len(lats)))

    pad = 0.001  # ~100 m, para trazer também as ruas da divisa
    bbox = f"{min(lons) - pad},{min(lats) - pad},{max(lons) + pad},{max(lats) + pad}"
    graph = street_graph(fetch_elements(f"map.json?bbox={bbox}"), polygon, scale)
    simplify(graph, SIMPLIFY_TOLERANCE_M / scale)
    graph = nx.convert_node_labels_to_integers(
        graph, ordering="sorted", label_attribute="osm_id"
    )

    nodes = [graph.nodes[v] for v in range(graph.number_of_nodes())]
    data = {
        "name": NAME,
        "attribution": ATTRIBUTION,
        "boundary": [[round(c, 7) for c in coords[n]] for n in ring],
        # o índice na lista é o número do vértice
        "nodes": [
            {
                "osm_id": n["osm_id"],
                "lon": round(n["lonlat"][0], 7),
                "lat": round(n["lonlat"][1], 7),
            }
            for n in nodes
        ],
        # comprimento em metros inteiros: a soma das distâncias fica exata
        "edges": [
            {"u": u, "v": v, "weight": max(1, round(w))}
            for u, v, w in graph.edges(data="weight")
        ],
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"{graph.number_of_nodes()} vértices e {graph.number_of_edges()} arestas "
        f"salvos em {OUTPUT}"
    )


if __name__ == "__main__":
    main()
