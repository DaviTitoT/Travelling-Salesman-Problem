"""Linha de comando: resolve uma instância e imprime a rota.

Execução: ``uv run ktsp --size 12 --k 10 --seed 42 --sa-seed 0``.
Todos os parâmetros têm valor padrão fixo e são impressos junto do resultado,
para que qualquer execução possa ser repetida a partir da própria saída.
"""

import argparse
from collections.abc import Sequence

from ktsp.annealing import AnnealingParams
from ktsp.baselines import MAX_BRUTE_FORCE_K, brute_force
from ktsp.pipeline import (
    DEFAULT_K,
    DEFAULT_SA_SEED,
    DEFAULT_SEED,
    DEFAULT_SIZE,
    solve,
)
from ktsp.solution import Route

DEFAULT_PARAMS = AnnealingParams()


def build_parser() -> argparse.ArgumentParser:
    """Define os argumentos da CLI."""
    parser = argparse.ArgumentParser(
        prog="ktsp",
        description="k-TSP do entregador de moto resolvido com Simulated Annealing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE, help="lado da grade")
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="pontos de entrega")
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help="semente da cidade"
    )
    parser.add_argument(
        "--sa-seed", type=int, default=DEFAULT_SA_SEED, help="semente do SA"
    )
    parser.add_argument(
        "--t0",
        type=float,
        default=DEFAULT_PARAMS.initial_temperature,
        help="temperatura inicial",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_PARAMS.cooling_rate,
        help="taxa de resfriamento",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_PARAMS.max_iterations,
        help="orçamento: vizinhos avaliados",
    )
    parser.add_argument(
        "--tabu-tenure",
        type=int,
        default=DEFAULT_PARAMS.tabu_tenure,
        help="tamanho da lista tabu do modo híbrido (0 = SA puro)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Resolve a instância descrita pelos argumentos e imprime o resultado."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        params = AnnealingParams(args.t0, args.alpha, args.iterations, args.tabu_tenure)
        run = solve(args.size, args.k, args.seed, args.sa_seed, params)
    except ValueError as error:
        parser.error(str(error))

    best = Route.from_order(run.steps[-1].best_order, run.table)
    initial = Route.from_order(run.initial, run.table)
    flags = " ".join(f"--{n.replace('_', '-')} {v}" for n, v in vars(args).items())
    print(f"Repetir esta execução: ktsp {flags}")
    print(f"Iterações executadas: {run.steps[-1].iteration}")
    print(f"Distância do vizinho mais próximo: {initial.cost:g}")
    if args.k <= MAX_BRUTE_FORCE_K:
        optimum = Route.from_order(brute_force(run.table), run.table)
        print(f"Distância ótima (força bruta): {optimum.cost:g}")
    print(f"Distância total (SA): {best.cost:g}")
    print(f"Base: {run.instance.base}")
    print(f"Ordem de visita: {' -> '.join(map(str, best.visits))}")
    print(f"Caminho completo: {' -> '.join(map(str, best.path))}")


if __name__ == "__main__":
    main()
