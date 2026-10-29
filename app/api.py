"""API HTTP simples para a interface React do k-TSP.

O mapa da interface (Leaflet) recebe posições em ``[lat, lng]``: no bairro real
são latitude e longitude; a grade sintética, sem geografia, é desenhada num
plano com ``[y, x]``. Rotas e arestas vão como números de vértice, e
``positions[v]`` dá a posição do vértice ``v``.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ktsp import pipeline
from ktsp.annealing import AnnealingParams
from ktsp.baselines import MAX_BRUTE_FORCE_K, brute_force
from ktsp.solution import Route, route_cost
from ktsp.street_map import load_street_map

DEFAULT_PARAMS = AnnealingParams()
MAX_K = 40


def _city_layer(city: str) -> dict:
    """Nome, unidade e contorno da cidade, para o mapa e os rótulos."""
    if city == "grid":
        return {
            "cityName": "Grade sintética",
            "geographic": False,
            "unit": "unidades",
            "boundary": [],
            "attribution": "",
        }
    street_map = load_street_map()
    return {
        "cityName": street_map.name,
        "geographic": True,
        "unit": "m",
        "boundary": [[lat, lon] for lon, lat in street_map.boundary],
        "attribution": street_map.attribution,
    }


def solve(payload: dict) -> dict:
    """Gera a instância, executa o SA e serializa os dados da visualização."""
    city = str(payload.get("city", pipeline.DEFAULT_CITY))
    size = int(payload.get("size", pipeline.DEFAULT_SIZE))
    k = int(payload.get("k", pipeline.DEFAULT_K))
    seed = int(payload.get("seed", pipeline.DEFAULT_SEED))
    sa_seed = int(payload.get("saSeed", pipeline.DEFAULT_SA_SEED))
    initial_temperature = float(
        payload.get("initialTemperature", DEFAULT_PARAMS.initial_temperature)
    )
    cooling_rate = float(payload.get("coolingRate", DEFAULT_PARAMS.cooling_rate))
    max_iterations = int(payload.get("maxIterations", DEFAULT_PARAMS.max_iterations))
    tabu_tenure = int(payload.get("tabuTenure", DEFAULT_PARAMS.tabu_tenure))
    if city not in pipeline.CITIES:
        raise ValueError("Cidade desconhecida.")
    if city == "grid" and not 4 <= size <= 25:
        raise ValueError("O tamanho da grade deve estar entre 4 e 25.")
    max_k = min(MAX_K, size * size - 1) if city == "grid" else MAX_K
    if not 1 <= k <= max_k:
        raise ValueError("A quantidade de entregas não é válida para esta cidade.")
    if initial_temperature <= 0 or not 0.9 <= cooling_rate <= 0.9999:
        raise ValueError("Confira a temperatura inicial e a taxa de resfriamento.")
    if not 10 <= max_iterations <= 200000:
        raise ValueError("O máximo de iterações deve estar entre 10 e 200.000.")
    if not 0 <= tabu_tenure <= 100:
        raise ValueError("A lista tabu deve ter entre 0 e 100 movimentos.")

    params = AnnealingParams(
        initial_temperature, cooling_rate, max_iterations, tabu_tenure
    )
    run = pipeline.solve(size, k, seed, sa_seed, params, city)
    instance, table, initial, steps = run.instance, run.table, run.initial, run.steps
    optimum = brute_force(table) if k <= MAX_BRUTE_FORCE_K else None
    graph = instance.graph
    positions = [  # pos é (x, y): longitude e latitude no bairro real
        [graph.nodes[v]["pos"][1], graph.nodes[v]["pos"][0]]
        for v in range(graph.number_of_nodes())
    ]

    # Limita a resposta ao navegador, mantendo início, fim e evolução visível.
    stride = max(1, len(steps) // 700)
    sampled = steps[::stride]
    if sampled[-1].iteration != steps[-1].iteration:
        sampled.append(steps[-1])

    best = Route.from_order(steps[-1].best_order, table)
    current = Route.from_order(steps[-1].current_order, table)
    result = {
        "city": city,
        **_city_layer(city),
        "size": size,
        "seed": seed,
        "saSeed": sa_seed,
        "tabuTenure": tabu_tenure,
        "k": k,
        "base": instance.base,
        "deliveries": list(instance.deliveries),
        "edges": [[u, v] for u, v in graph.edges],
        "positions": positions,
        "steps": [
            {
                "iteration": step.iteration,
                "temperature": step.temperature,
                "currentCost": step.current_cost,
                "bestCost": step.best_cost,
                "currentPath": list(Route.from_order(step.current_order, table).path),
                "bestPath": list(Route.from_order(step.best_order, table).path),
                "bestOrder": list(step.best_order),
            }
            for step in sampled
        ],
        "initialCost": route_cost(initial, table),
        "bestCost": best.cost,
        "bestVisits": list(best.visits),
        "bestVertexPath": list(best.path),
        "currentCost": current.cost,
        "optimumCost": route_cost(optimum, table) if optimum is not None else None,
        "iterations": steps[-1].iteration,
        # Primeira iteração em que a melhor rota final apareceu.
        "foundAt": next(
            step.iteration for step in steps if step.best_cost == best.cost
        ),
    }
    return result


class Handler(BaseHTTPRequestHandler):
    """Atende requisições da aplicação local."""

    def _json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self) -> None:
        """Permite preflight CORS quando a interface roda em outra origem."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        """Executa uma instância solicitada pela interface web."""
        if self.path != "/api/solve":
            self._json(404, {"error": "Rota não encontrada."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            self._json(200, solve(payload))
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(400, {"error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        """Mantém o terminal livre de logs por requisição."""


def main() -> None:
    """Inicia a API usada pelo Vite durante o desenvolvimento."""
    address = ("127.0.0.1", 8000)
    print(f"API k-TSP disponível em http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, Handler).serve_forever()


if __name__ == "__main__":
    main()
