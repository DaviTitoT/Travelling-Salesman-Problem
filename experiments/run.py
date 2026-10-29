"""Experimentos do Simulated Annealing sobre instâncias geradas.

Varia k e a taxa de resfriamento α em várias cidades, roda o SA com várias
sementes em cada uma e mede o desvio em relação à melhor rota conhecida: o ótimo
exato para k pequeno ou a melhor rota achada nas execuções.

Execução: ``uv run python experiments/run.py`` (``--help`` lista os parâmetros).
Todos os parâmetros têm padrão fixo e são gravados em ``params.json`` junto dos
resultados, com o commit e as versões do ambiente; só a coluna ``seconds``
depende da máquina.
"""

import argparse
import json
import math
import platform
import random
import subprocess
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ktsp.annealing import AnnealingParams, anneal
from ktsp.baselines import MAX_BRUTE_FORCE_K, brute_force, nearest_neighbor
from ktsp.distances import build_distance_table
from ktsp.instance import generate_instance
from ktsp.solution import route_cost

PACKAGES = ("networkx", "pandas", "matplotlib")


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
        "--sa-seeds",
        type=int,
        nargs="+",
        default=list(range(10)),
        help="sementes do SA (uma execução por semente em cada cidade e α)",
    )
    parser.add_argument("--t0", type=float, default=100.0, help="temperatura inicial")
    parser.add_argument(
        "--iterations",
        type=int,
        default=20_000,
        help="orçamento: vizinhos avaliados por execução",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results",
        help="pasta onde cada execução cria a subpasta <timestamp>-<commit>",
    )
    return parser


def run_experiments(args: argparse.Namespace) -> pd.DataFrame:
    """Executa todas as combinações e devolve uma linha por execução do SA.

    Cada combinação de cidade e α roda uma vez por semente do SA, porque o
    resultado de um algoritmo com sorteio é uma distribuição, não um número.
    """
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
                for sa_seed in args.sa_seeds:
                    start = time.perf_counter()
                    best_cost, found_at = math.inf, 0
                    for step in anneal(table, initial, params, random.Random(sa_seed)):
                        if step.best_cost < best_cost:
                            best_cost, found_at = step.best_cost, step.iteration
                    rows.append(
                        {
                            "k": k,
                            "seed": seed,
                            "alpha": alpha,
                            "sa_seed": sa_seed,
                            "nn_cost": route_cost(initial, table),
                            "sa_cost": best_cost,
                            "opt_cost": optimum,
                            "found_at": found_at,
                            "iterations": step.iteration,
                            "seconds": time.perf_counter() - start,
                        }
                    )
    df = pd.DataFrame(rows)
    # Referência: o ótimo (força bruta) quando existe; senão, a melhor rota achada
    # em todas as execuções daquela cidade, que pode não ser o ótimo.
    best_found = df.groupby(["k", "seed"]).sa_cost.transform("min")
    df["reference"] = df.opt_cost.fillna(best_found)
    df["reference_is_optimum"] = df.opt_cost.notna()
    df["deviation_pct"] = 100 * (df.sa_cost - df.reference) / df.reference
    df["hit"] = df.sa_cost == df.reference
    df["improvement_over_nn_pct"] = 100 * (df.nn_cost - df.sa_cost) / df.nn_cost
    return df


def environment() -> dict:
    """Versão do código e do ambiente, para rastrear como os resultados nasceram."""

    def git(*command: str) -> str | None:
        result = subprocess.run(
            ["git", *command], capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None

    status = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "HEAD"),
        "uncommitted_changes": bool(status) if status is not None else None,
        "python": platform.python_version(),
        "packages": {name: version(name) for name in PACKAGES},
    }


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
    env = environment()
    # Uma pasta por execução, <timestamp UTC>-<commit>, para nunca sobrescrever
    # resultados anteriores e saber de qual versão do código cada um veio.
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    results_dir = args.output / f"{timestamp}-{(env['commit'] or 'sem-commit')[:7]}"
    results_dir.mkdir(parents=True)
    params = {k: v for k, v in vars(args).items() if k != "output"}
    record = {"params": params, "environment": env}
    (results_dir / "params.json").write_text(json.dumps(record, indent=2) + "\n")
    df = run_experiments(args)
    df.to_csv(results_dir / "results.csv", index=False)

    summary = df.groupby(["k", "alpha"]).agg(
        runs=("sa_cost", "size"),
        reference_is_optimum=("reference_is_optimum", "all"),
        deviation_mean_pct=("deviation_pct", "mean"),
        deviation_std_pct=("deviation_pct", "std"),
        hit_rate_pct=("hit", lambda hits: 100 * hits.mean()),
        improvement_over_nn_pct=("improvement_over_nn_pct", "mean"),
        found_at_mean=("found_at", "mean"),
        seconds_mean=("seconds", "mean"),
    )
    summary.to_csv(results_dir / "summary.csv")
    print(summary.round(3).to_string())

    plot_by_k(
        df,
        "improvement_over_nn_pct",
        "Melhoria média sobre vizinho mais próximo (%)",
        results_dir / "improvement_over_nn.png",
    )
    plot_by_k(
        df,
        "deviation_pct",
        "Desvio médio da melhor rota conhecida (%)",
        results_dir / "deviation.png",
    )
    plot_by_k(
        df.assign(hit=100 * df.hit),
        "hit",
        "Taxa de acerto da melhor rota conhecida (%)",
        results_dir / "hit_rate.png",
    )
    print(f"Resultados gravados em {results_dir}")


if __name__ == "__main__":
    main()
