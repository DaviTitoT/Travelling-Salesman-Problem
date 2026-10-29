"""API HTTP simples para a interface React do k-TSP."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ktsp import pipeline
from ktsp.annealing import AnnealingParams
from ktsp.baselines import MAX_BRUTE_FORCE_K, brute_force
from ktsp.solution import Route, route_cost

DEFAULT_PARAMS = AnnealingParams()


def _path_positions(
    path: tuple[int, ...], positions: dict[int, list[int]]
) -> list[list[int]]:
    """Converte os vértices do caminho em coordenadas para o mapa."""
    return [positions[node] for node in path]


def solve(payload: dict) -> dict:
    """Gera a instância, executa o SA e serializa os dados da visualização."""
    size = int(payload.get("size", pipeline.DEFAULT_SIZE))
    k = int(payload.get("k", pipeline.DEFAULT_K))
    seed = int(payload.get("seed", pipeline.DEFAULT_SEED))
    sa_seed = int(payload.get("saSeed", pipeline.DEFAULT_SA_SEED))
    initial_temperature = float(
        payload.get("initialTemperature", DEFAULT_PARAMS.initial_temperature)
    )
    cooling_rate = float(payload.get("coolingRate", DEFAULT_PARAMS.cooling_rate))
    max_iterations = int(payload.get("maxIterations", DEFAULT_PARAMS.max_iterations))
    if not 4 <= size <= 25:
        raise ValueError("O tamanho da grade deve estar entre 4 e 25.")
    if not 1 <= k <= min(40, size * size - 1):
        raise ValueError("A quantidade de entregas não é válida para esta grade.")
    if initial_temperature <= 0 or not 0.9 <= cooling_rate <= 0.9999:
        raise ValueError("Confira a temperatura inicial e a taxa de resfriamento.")
    if not 10 <= max_iterations <= 200000:
        raise ValueError("O máximo de iterações deve estar entre 10 e 200.000.")

    params = AnnealingParams(initial_temperature, cooling_rate, max_iterations)
    run = pipeline.solve(size, k, seed, sa_seed, params)
    instance, table, initial, steps = run.instance, run.table, run.initial, run.steps
    optimum = brute_force(table) if k <= MAX_BRUTE_FORCE_K else None
    positions = {
        node: [column, row] for node, (row, column) in instance.graph.nodes(data="pos")
    }

    # Limita a resposta ao navegador, mantendo início, fim e evolução visível.
    stride = max(1, len(steps) // 700)
    sampled = steps[::stride]
    if sampled[-1].iteration != steps[-1].iteration:
        sampled.append(steps[-1])

    best = Route.from_order(steps[-1].best_order, table)
    current = Route.from_order(steps[-1].current_order, table)
    result = {
        "size": size,
        "seed": seed,
        "saSeed": sa_seed,
        "k": k,
        "base": positions[instance.base],
        "deliveries": [positions[node] for node in instance.deliveries],
        "edges": [[positions[u], positions[v]] for u, v in instance.graph.edges],
        "positions": positions,
        "steps": [
            {
                "iteration": step.iteration,
                "temperature": step.temperature,
                "currentCost": step.current_cost,
                "bestCost": step.best_cost,
                "currentPath": _path_positions(
                    Route.from_order(step.current_order, table).path, positions
                ),
                "bestPath": _path_positions(
                    Route.from_order(step.best_order, table).path, positions
                ),
                "bestOrder": list(step.best_order),
            }
            for step in sampled
        ],
        "initialCost": route_cost(initial, table),
        "bestCost": best.cost,
        "bestPath": _path_positions(best.path, positions),
        "bestVisits": list(best.visits),
        "bestVertexPath": list(best.path),
        "currentCost": current.cost,
        "optimumCost": route_cost(optimum, table) if optimum is not None else None,
        "iterations": steps[-1].iteration,
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
