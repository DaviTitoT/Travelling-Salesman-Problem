"""Experimentos do Simulated Annealing sobre instâncias geradas.

Varia k, a taxa de resfriamento α, a solução inicial e a semente. Compara o SA
com o vizinho mais próximo, a ordem aleatória e, para k pequeno, o ótimo exato.

Execução: ``uv run python experiments/run.py``. Saída em ``experiments/results/``.
"""

import random
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ktsp.annealing import AnnealingParams, anneal
from ktsp.baselines import (
    MAX_BRUTE_FORCE_K,
    brute_force,
    nearest_neighbor,
    random_order,
)
from ktsp.distances import build_distance_table
from ktsp.instance import generate_instance
from ktsp.solution import route_cost

GRID_SIZE = 15
K_VALUES = (6, 8, 15, 30)
COOLING_RATES = (0.99, 0.995, 0.999)
INITIAL_SOLUTIONS = ("nearest_neighbor", "random")
SEEDS = range(10)
INITIAL_TEMPERATURE = 100.0
MAX_ITERATIONS = 20_000
RESULTS_DIR = Path(__file__).parent / "results"
INITIAL_SOLUTION_LABELS = {
    "nearest_neighbor": "Vizinho mais próximo",
    "random": "Aleatória",
}


def run_experiments() -> pd.DataFrame:
    """Executa todas as combinações e devolve uma linha por execução do SA."""
    rows = []
    for k in K_VALUES:
        for seed in SEEDS:
            table = build_distance_table(
                generate_instance(GRID_SIZE, GRID_SIZE, k, seed)
            )
            initial = nearest_neighbor(table)
            optimum = (
                route_cost(brute_force(table), table)
                if k <= MAX_BRUTE_FORCE_K
                else None
            )
            nn_cost = route_cost(initial, table)
            for initial_solution in INITIAL_SOLUTIONS:
                initial_order = (
                    initial
                    if initial_solution == "nearest_neighbor"
                    else random_order(table, random.Random(seed))
                )
                initial_cost = route_cost(initial_order, table)
                for alpha in COOLING_RATES:
                    params = AnnealingParams(INITIAL_TEMPERATURE, alpha, MAX_ITERATIONS)
                    start = time.perf_counter()
                    *_, last = anneal(table, initial_order, params, random.Random(seed))
                    rows.append(
                        {
                            "k": k,
                            "alpha": alpha,
                            "seed": seed,
                            "initial_solution": initial_solution,
                            "initial_cost": initial_cost,
                            "nn_cost": nn_cost,
                            "sa_cost": last.best_cost,
                            "opt_cost": optimum,
                            "iterations": last.iteration,
                            "seconds": time.perf_counter() - start,
                        }
                    )
    df = pd.DataFrame(rows)
    df["improvement_over_nn_pct"] = 100 * (df.nn_cost - df.sa_cost) / df.nn_cost
    df["improvement_over_initial_pct"] = (
        100 * (df.initial_cost - df.sa_cost) / df.initial_cost
    )
    df["gap_to_opt_pct"] = 100 * (df.sa_cost - df.opt_cost) / df.opt_cost
    return df


def plot_by_k(df: pd.DataFrame, column: str, ylabel: str, path: Path) -> None:
    """Gráfico de barras da média de ``column`` por k, estratégia e α."""
    means = df.pivot_table(
        index="k",
        columns=["initial_solution", "alpha"],
        values=column,
        aggfunc="mean",
    )
    means.columns = [
        f"{INITIAL_SOLUTION_LABELS[strategy]} | α={alpha:g}"
        for strategy, alpha in means.columns
    ]
    ax = means.plot.bar(rot=0, figsize=(7, 4))
    ax.set_xlabel("Quantidade de entregas (k)")
    ax.set_ylabel(ylabel)
    ax.legend(title="Solução inicial | resfriamento")
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=150)
    plt.close(ax.figure)


def plot_initial_solution_comparison(df: pd.DataFrame, path: Path) -> None:
    """Compara custos iniciais e finais médios das estratégias por k."""
    means = df.groupby(["k", "initial_solution"])[["initial_cost", "sa_cost"]].mean()
    comparison = pd.DataFrame(index=sorted(df.k.unique()))
    for strategy, label in INITIAL_SOLUTION_LABELS.items():
        strategy_means = means.xs(strategy, level="initial_solution")
        comparison[f"{label} (inicial)"] = strategy_means.initial_cost
        comparison[f"{label} (final)"] = strategy_means.sa_cost

    ax = comparison.plot.bar(rot=0, figsize=(8, 4))
    ax.set_xlabel("Quantidade de entregas (k)")
    ax.set_ylabel("Distância média")
    ax.legend(title="Solução")
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=150)
    plt.close(ax.figure)


def main() -> None:
    """Roda os experimentos e salva CSV, resumo e gráficos."""
    RESULTS_DIR.mkdir(exist_ok=True)
    df = run_experiments()
    df.to_csv(RESULTS_DIR / "results.csv", index=False)

    summary = df.groupby(["initial_solution", "k", "alpha"])[
        [
            "initial_cost",
            "sa_cost",
            "improvement_over_nn_pct",
            "improvement_over_initial_pct",
            "gap_to_opt_pct",
            "iterations",
            "seconds",
        ]
    ].mean()
    summary.to_csv(RESULTS_DIR / "summary.csv")
    print(summary.round(3).to_string())

    plot_by_k(
        df,
        "improvement_over_nn_pct",
        "Melhoria média sobre vizinho mais próximo (%)",
        RESULTS_DIR / "improvement_over_nn.png",
    )
    plot_by_k(
        df,
        "improvement_over_initial_pct",
        "Melhoria média sobre a solução inicial (%)",
        RESULTS_DIR / "improvement_by_initial_solution.png",
    )
    plot_by_k(
        df[df.k <= MAX_BRUTE_FORCE_K],
        "gap_to_opt_pct",
        "Gap médio para o ótimo (%)",
        RESULTS_DIR / "gap_to_optimum.png",
    )
    plot_initial_solution_comparison(
        df, RESULTS_DIR / "initial_solution_comparison.png"
    )


if __name__ == "__main__":
    main()
