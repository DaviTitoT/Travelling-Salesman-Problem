"""API HTTP simples para a interface React do k-TSP.

O mapa recebe ``positions`` indexado pelo id do vértice. Cada posição segue o
formato do Leaflet: ``[lat, lng]`` no bairro real e ``[y, x]`` na grade.
Rotas e arestas contêm ids de vértices, não coordenadas.
"""

import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ktsp import pipeline
from ktsp.annealing import AnnealingParams
from ktsp.baselines import MAX_BRUTE_FORCE_K, brute_force
from ktsp.instance import Instance
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
    """Gera duas rotas com a mesma lista de entregas e bases distintas."""
    city = str(payload.get("city", pipeline.DEFAULT_CITY))
    size = int(payload.get("size", pipeline.DEFAULT_SIZE))
    k = int(payload.get("k", pipeline.DEFAULT_K))
    seed = int(payload.get("seed", pipeline.DEFAULT_SEED))
    sa_seed = int(payload.get("saSeed", pipeline.DEFAULT_SA_SEED))
    route_base = payload.get("routeBase", "selected")
    random_seed_value = payload.get("randomSeed")
    random_seed = (
        int(random_seed_value)
        if random_seed_value is not None
        else random.SystemRandom().getrandbits(32)
    )
    requested_base = payload.get("base")
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
    if initial_temperature <= 0 or not 0.9 <= cooling_rate <= 0.9999:
        raise ValueError("Confira a temperatura inicial e a taxa de resfriamento.")
    if not 10 <= max_iterations <= 200000:
        raise ValueError("O máximo de iterações deve estar entre 10 e 200.000.")
    if not 0 <= tabu_tenure <= 100:
        raise ValueError("A lista tabu deve ter entre 0 e 100 movimentos.")
    if route_base not in ("selected", "random"):
        raise ValueError("A base exibida deve ser 'selected' ou 'random'.")
    if random_seed < 0:
        raise ValueError("A semente da base aleatória não pode ser negativa.")
    if requested_base is not None and (
        not isinstance(requested_base, int) or isinstance(requested_base, bool)
    ):
        raise ValueError("A base deve ser informada como id de vértice inteiro.")

    params = AnnealingParams(
        initial_temperature, cooling_rate, max_iterations, tabu_tenure
    )
    generated = pipeline.build_instance(city, size, k, seed)
    graph = generated.graph
    if not 1 <= k <= min(MAX_K, graph.number_of_nodes() - 2):
        raise ValueError(
            "A quantidade de entregas deve reservar duas posições para as bases."
        )

    selected_base = generated.base if requested_base is None else requested_base
    if selected_base not in graph:
        if city == "grid":
            raise ValueError("A posição da base deve estar dentro da grade.")
        raise ValueError("O id da base não existe no mapa da cidade.")

    # Se a base escolhida era uma entrega, a base sorteada ocupa esse lugar na
    # lista; assim as duas bases e todos os pontos de entrega seguem distintos.
    deliveries = tuple(
        generated.base if delivery == selected_base else delivery
        for delivery in generated.deliveries
    )
    selected_instance = Instance(graph=graph, base=selected_base, deliveries=deliveries)

    random_candidates = sorted(
        node for node in graph if node != selected_base and node not in deliveries
    )
    random_base = random.Random(random_seed).choice(random_candidates)
    random_instance = Instance(graph=graph, base=random_base, deliveries=deliveries)
    instances = {"selected": selected_instance, "random": random_instance}
    runs = {
        strategy: pipeline.solve_instance(instance, sa_seed, params)
        for strategy, instance in instances.items()
    }

    run = runs[route_base]
    instance, table, initial, steps = run.instance, run.table, run.initial, run.steps
    optimum = brute_force(table) if k <= MAX_BRUTE_FORCE_K else None
    # Os dois mapas suportados usam ids inteiros contíguos de 0 a n-1.
    positions = [
        [graph.nodes[node]["pos"][1], graph.nodes[node]["pos"][0]]
        for node in range(graph.number_of_nodes())
    ]

    # Limita a resposta ao navegador, mantendo início, fim e evolução visível.
    stride = max(1, len(steps) // 700)
    sampled = steps[::stride]
    if sampled[-1].iteration != steps[-1].iteration:
        sampled.append(steps[-1])

    best = Route.from_order(steps[-1].best_order, table)
    current = Route.from_order(steps[-1].current_order, table)
    comparisons = []
    for strategy, strategy_run in runs.items():
        strategy_steps = strategy_run.steps
        strategy_table = strategy_run.table
        strategy_best = Route.from_order(strategy_steps[-1].best_order, strategy_table)
        strategy_initial = Route.from_order(strategy_run.initial, strategy_table)
        strategy_initial_cost = strategy_initial.cost
        comparison_base = strategy_run.instance.base
        comparisons.append(
            {
                "strategy": strategy,
                "base": comparison_base,
                "baseNode": comparison_base,
                "basePosition": positions[comparison_base],
                "initialCost": strategy_initial_cost,
                "bestCost": strategy_best.cost,
                "improvementPct": (
                    100
                    * (strategy_initial_cost - strategy_best.cost)
                    / strategy_initial_cost
                ),
                "initialVisits": list(strategy_initial.visits),
                "bestVisits": list(strategy_best.visits),
                "bestVertexPath": list(strategy_best.path),
                "iterations": strategy_steps[-1].iteration,
            }
        )

    result = {
        "city": city,
        **_city_layer(city),
        "size": size,
        "seed": seed,
        "saSeed": sa_seed,
        "tabuTenure": tabu_tenure,
        "k": k,
        "routeBase": route_base,
        "randomSeed": random_seed,
        "comparisons": comparisons,
        "base": selected_instance.base,
        "displayBase": instance.base,
        "basePosition": positions[selected_instance.base],
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
