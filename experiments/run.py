"""Experimentos do Simulated Annealing sobre instâncias geradas.

Varia k e a taxa de resfriamento α em várias sementes e compara o SA com o
vizinho mais próximo (solução inicial) e, para k pequeno, com o ótimo exato.

Execução: ``uv run python experiments/run.py`` (``--help`` lista os parâmetros).
Todos os parâmetros têm padrão fixo e são gravados em ``params.json`` junto dos
resultados; só a coluna ``seconds`` depende da máquina.
"""

import argparse
import json
import random
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ktsp.annealing import AnnealingParams, anneal
from ktsp.baselines import MAX_BRUTE_FORCE_K, brute_force, nearest_neighbor
from ktsp.distances import build_distance_table
from ktsp.instance import generate_instance
from ktsp.pipeline import DEFAULT_SA_SEED
from ktsp.solution import route_cost


def build_parser() -> argparse.ArgumentParser:
    """Define os parâmetros da grade de experimentos."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--grid-size", type=int, default=15, help="lado da grade")
    parser.add_argument(
        "--k", type=int, nargs="+", default=[6, 8, 15, 30], help="valores de k"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        nargs="+",
        default=[0.99, 0.995, 0.999],
        help="taxas de resfriamento",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(range(10)),
        help="sementes das cidades",
    )
    parser.add_argument(
        "--sa-seed", type=int, default=DEFAULT_SA_SEED, help="semente do SA"
    )
    parser.add_argument("--t0", type=float, default=100.0, help="temperatura inicial")
    parser.add_argument(
        "--iterations", type=int, default=20_000, help="máximo de iterações"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results",
        help="pasta de saída",
    )
    return parser


def run_experiments(args: argparse.Namespace) -> pd.DataFrame:
    """Executa todas as combinações e devolve uma linha por execução do SA."""
    rows = []
    for k in args.k:
        for seed in args.seeds:
            table = build_distance_table(
                generate_instance(args.grid_size, args.grid_size, k, seed)
            )
            initial = nearest_neighbor(table)
            optimum = (
                route_cost(brute_force(table), table)
                if k <= MAX_BRUTE_FORCE_K
                else None
            )
            for alpha in args.alpha:
                params = AnnealingParams(args.t0, alpha, args.iterations)
                start = time.perf_counter()
                rng = random.Random(args.sa_seed)
                *_, last = anneal(table, initial, params, rng)
                rows.append(
                    {
                        "k": k,
                        "alpha": alpha,
                        "seed": seed,
                        "nn_cost": route_cost(initial, table),
                        "sa_cost": last.best_cost,
                        "opt_cost": optimum,
                        "iterations": last.iteration,
                        "seconds": time.perf_counter() - start,
                    }
                )
    df = pd.DataFrame(rows)
    df["improvement_over_nn_pct"] = 100 * (df.nn_cost - df.sa_cost) / df.nn_cost
    df["gap_to_opt_pct"] = 100 * (df.sa_cost - df.opt_cost) / df.opt_cost
    return df


def plot_by_k(df: pd.DataFrame, column: str, ylabel: str, path: Path) -> None:
    """Gráfico de barras da média de ``column`` por k, uma barra por α."""
    means = df.pivot_table(index="k", columns="alpha", values=column, aggfunc="mean")
    ax = means.plot.bar(rot=0, figsize=(7, 4))
    ax.set_ylabel(ylabel)
    ax.legend(title="α")
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=150)
    plt.close(ax.figure)


def main() -> None:
    """Roda os experimentos e salva parâmetros, CSV, resumo e gráficos."""
    args = build_parser().parse_args()
    results_dir = args.output
    results_dir.mkdir(parents=True, exist_ok=True)
    params = {k: v for k, v in vars(args).items() if k != "output"}
    (results_dir / "params.json").write_text(json.dumps(params, indent=2) + "\n")
    df = run_experiments(args)
    df.to_csv(results_dir / "results.csv", index=False)

    summary = df.groupby(["k", "alpha"])[
        ["improvement_over_nn_pct", "gap_to_opt_pct", "iterations", "seconds"]
    ].mean()
    summary.to_csv(results_dir / "summary.csv")
    print(summary.round(3).to_string())

    plot_by_k(
        df,
        "improvement_over_nn_pct",
        "Melhoria média sobre vizinho mais próximo (%)",
        results_dir / "improvement_over_nn.png",
    )
    plot_by_k(
        df[df.k <= MAX_BRUTE_FORCE_K],
        "gap_to_opt_pct",
        "Gap médio para o ótimo (%)",
        results_dir / "gap_to_optimum.png",
    )


if __name__ == "__main__":
    main()
