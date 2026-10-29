"""API HTTP simples para a interface React do k-TSP."""

import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ktsp.annealing import AnnealingParams, anneal
from ktsp.baselines import (
    MAX_BRUTE_FORCE_K,
    brute_force,
    nearest_neighbor,
)
from ktsp.distances import build_distance_table
from ktsp.instance import Instance, generate_instance
from ktsp.solution import Route, route_cost


def _path_positions(
    path: tuple[int, ...], positions: dict[int, list[int]]
) -> list[list[int]]:
    """Converte os vértices do caminho em coordenadas para o mapa."""
    return [positions[node] for node in path]


def solve(payload: dict) -> dict:
    """Compara as rotas a partir da base escolhida e de uma base aleatória."""
    size = int(payload.get("size", 12))
    k = int(payload.get("k", 10))
    seed = int(payload.get("seed", 42))
    initial_temperature = float(payload.get("initialTemperature", 100))
    cooling_rate = float(payload.get("coolingRate", 0.995))
    max_iterations = int(payload.get("maxIterations", 5000))
    route_base = payload.get("routeBase", "selected")
    requested_base = payload.get("base")
    random_seed_value = payload.get("randomSeed")
    random_seed = (
        int(random_seed_value)
        if random_seed_value is not None
        else random.SystemRandom().getrandbits(32)
    )
    if not 4 <= size <= 25:
        raise ValueError("O tamanho da grade deve estar entre 4 e 25.")
    if not 1 <= k <= min(40, size * size - 2):
        raise ValueError(
            "A quantidade de entregas deve reservar duas posições para as bases."
        )
    if initial_temperature <= 0 or not 0.9 <= cooling_rate <= 0.9999:
        raise ValueError("Confira a temperatura inicial e a taxa de resfriamento.")
    if not 10 <= max_iterations <= 200000:
        raise ValueError("O máximo de iterações deve estar entre 10 e 200.000.")
    if route_base not in ("selected", "random"):
        raise ValueError("A base exibida deve ser 'selected' ou 'random'.")
    if random_seed < 0:
        raise ValueError("A semente da base aleatória não pode ser negativa.")

    instance = generate_instance(size, size, k, seed)
    if requested_base is not None:
        if (
            not isinstance(requested_base, list)
            or len(requested_base) != 2
            or not all(isinstance(value, int) for value in requested_base)
        ):
            raise ValueError("A base deve ser informada como [coluna, linha].")
        column, row = requested_base
        if not 0 <= column < size or not 0 <= row < size:
            raise ValueError("A posição da base deve estar dentro da grade.")
        node_by_position = {
            (node_column, node_row): node
            for node, (node_row, node_column) in instance.graph.nodes(data="pos")
        }
        base_node = node_by_position[(column, row)]
        delivery_rng = random.Random(seed)
        deliveries = tuple(
            delivery_rng.sample(
                sorted(node for node in instance.graph if node != base_node), k
            )
        )
        instance = Instance(graph=instance.graph, base=base_node, deliveries=deliveries)
    fixed_base = instance.base
    available_bases = sorted(
        node for node in instance.graph if node not in instance.deliveries
    )
    random_candidates = [node for node in available_bases if node != fixed_base]
    if not random_candidates:
        random_candidates = available_bases
    random_base = random.Random(random_seed).choice(random_candidates)
    instances = {
        "selected": instance,
        "random": Instance(
            graph=instance.graph,
            base=random_base,
            deliveries=instance.deliveries,
        ),
    }
    tables = {
        strategy: build_distance_table(strategy_instance)
        for strategy, strategy_instance in instances.items()
    }
    params = AnnealingParams(initial_temperature, cooling_rate, max_iterations)
    runs = {
        strategy: list(
            anneal(
                tables[strategy],
                nearest_neighbor(tables[strategy]),
                params,
                random.Random(seed),
            )
        )
        for strategy in instances
    }
    table = tables[route_base]
    steps = runs[route_base]
    initial = nearest_neighbor(table)
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
    comparisons = []
    for strategy, strategy_steps in runs.items():
        strategy_table = tables[strategy]
        strategy_initial = nearest_neighbor(strategy_table)
        strategy_best = Route.from_order(strategy_steps[-1].best_order, strategy_table)
        strategy_base_node = instances[strategy].base
        strategy_initial_cost = route_cost(strategy_initial, strategy_table)
        comparisons.append(
            {
                "strategy": strategy,
                "base": positions[instances[strategy].base],
                "initialCost": strategy_initial_cost,
                "bestCost": strategy_best.cost,
                "improvementPct": (
                    100
                    * (strategy_initial_cost - strategy_best.cost)
                    / strategy_initial_cost
                ),
                "initialVisits": list(
                    Route.from_order(strategy_initial, strategy_table).visits
                ),
                "bestVisits": list(strategy_best.visits),
                "bestVertexPath": list(strategy_best.path),
                "baseNode": strategy_base_node,
                "iterations": strategy_steps[-1].iteration,
            }
        )
    result = {
        "size": size,
        "seed": seed,
        "k": k,
        "routeBase": route_base,
        "randomSeed": random_seed,
        "comparisons": comparisons,
        "base": positions[instance.base],
        "displayBase": positions[instances[route_base].base],
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
