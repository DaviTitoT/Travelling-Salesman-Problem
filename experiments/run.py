"""Experimentos do Simulated Annealing sobre instâncias geradas.

Varia k e a taxa de resfriamento α em várias cidades, roda o SA com várias
sementes em cada uma e mede o desvio em relação à melhor rota conhecida: o ótimo
exato para k pequeno ou a melhor rota achada nas execuções.

Execução: ``uv run python experiments/run.py`` (``--help`` lista os parâmetros).
Para repetir uma execução anterior e comparar os resultados:
``uv run python experiments/run.py --params <pasta da execução>/params.json``.
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
import sys
import time
from array import array
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
    parser.add_argument(
        "--params",
        type=Path,
        help="params.json de uma execução anterior: repete os parâmetros dela "
        "(flags explícitas têm prioridade), confere o ambiente e compara os "
        "resultados ao final",
    )
    parser.add_argument(
        "--allow-env-mismatch",
        action="store_true",
        help="roda mesmo com Python ou bibliotecas em versões diferentes das do "
        "params.json",
    )
    return parser


# Opções que controlam o script, não o experimento: não vão para params.json.
SCRIPT_OPTIONS = {"output", "params", "allow_env_mismatch"}


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, dict | None]:
    """Lê os argumentos; com ``--params``, os valores do arquivo viram o padrão.

    Returns:
        Os argumentos e o registro lido do ``params.json`` (ou ``None``).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.params is None:
        return args, None
    try:
        record = json.loads(args.params.read_text())
    except (OSError, json.JSONDecodeError) as error:
        parser.error(f"não foi possível ler {args.params}: {error}")
    saved = record.get("params", record)  # params.json antigo: só os parâmetros
    unknown = set(saved) - (set(vars(args)) - SCRIPT_OPTIONS)
    if unknown:
        parser.error(f"parâmetros desconhecidos em {args.params}: {sorted(unknown)}")
    parser.set_defaults(**saved)
    return parser.parse_args(argv), record


def check_environment(saved: dict | None, current: dict) -> tuple[list[str], list[str]]:
    """Compara o ambiente gravado com o atual.

    Args:
        saved: Campo ``environment`` do ``params.json`` original.
        current: Ambiente atual, de ``environment()``.

    Returns:
        Incompatibilidades (podem mudar os resultados) e avisos.
    """
    if saved is None:
        return [], ["o params.json não registra o ambiente; nada foi conferido"]
    problems, warnings = [], []
    # O módulo random só garante a mesma sequência dentro da mesma versão maior.menor.
    if saved["python"].rsplit(".", 1)[0] != current["python"].rsplit(".", 1)[0]:
        problems.append(
            f"Python {saved['python']} no original, {current['python']} aqui"
        )
    for name, wanted in saved["packages"].items():
        found = current["packages"].get(name)
        if found != wanted:
            problems.append(f"{name} {wanted} no original, {found} aqui")
    if saved["commit"] != current["commit"]:
        warnings.append(
            f"commit diferente ({str(saved['commit'])[:7]} no original, "
            f"{str(current['commit'])[:7]} aqui): os resultados mudam se o "
            "algoritmo mudou"
        )
    if saved["uncommitted_changes"]:
        warnings.append("o original tinha alterações não commitadas")
    if current["uncommitted_changes"]:
        warnings.append("este código tem alterações não commitadas")
    return problems, warnings


def compare_results(original: Path, new: Path) -> str:
    """Compara dois ``results.csv`` ignorando ``seconds``, a única coluna que muda."""
    old = pd.read_csv(original).drop(columns="seconds")
    cur = pd.read_csv(new).drop(columns="seconds")
    if list(old.columns) != list(cur.columns) or len(old) != len(cur):
        return "não comparáveis: colunas ou número de execuções diferentes"
    differs = (old.ne(cur) & ~(old.isna() & cur.isna())).any(axis=1).sum()
    if differs == 0:
        return f"idênticos ({len(old)} execuções, sem contar o tempo)"
    return f"{differs} de {len(old)} execuções com resultados diferentes"


def run_experiments(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Executa as combinações e devolve resultados e evolução média por iteração.

    Cada combinação de cidade e α roda uma vez por semente do SA, porque o
    resultado de um algoritmo com sorteio é uma distribuição, não um número.
    A evolução é normalizada pelo custo inicial de cada instância, permitindo
    comparar cidades de tamanhos diferentes.
    """
    rows = []
    progress: dict[tuple[int, float], dict[str, array]] = {}
    for k in args.k:
        for seed in args.seeds:
            table = build_distance_table(
                generate_instance(args.grid_size, args.grid_size, k, seed)
            )
            initial = nearest_neighbor(table)
            nn_cost = route_cost(initial, table)
            optimum = (
                route_cost(brute_force(table), table)
                if k <= MAX_BRUTE_FORCE_K
                else None
            )
            for alpha in args.alpha:
                params = AnnealingParams(args.t0, alpha, args.iterations)
                for sa_seed in args.sa_seeds:
                    start = time.perf_counter()
                    key = (k, alpha)
                    if key not in progress:
                        length = args.iterations + 1
                        progress[key] = {
                            name: array("d", [0.0]) * length
                            for name in (
                                "counts",
                                "current_improvement",
                                "best_improvement",
                                "accepted",
                                "temperature",
                            )
                        }
                    totals = progress[key]
                    best_cost, found_at = math.inf, 0
                    for step in anneal(table, initial, params, random.Random(sa_seed)):
                        if step.best_cost < best_cost:
                            best_cost, found_at = step.best_cost, step.iteration
                        iteration = step.iteration
                        totals["counts"][iteration] += 1
                        totals["current_improvement"][iteration] += (
                            100 * (nn_cost - step.current_cost) / nn_cost
                        )
                        totals["best_improvement"][iteration] += (
                            100 * (nn_cost - step.best_cost) / nn_cost
                        )
                        totals["accepted"][iteration] += step.accepted
                        totals["temperature"][iteration] += step.temperature
                    rows.append(
                        {
                            "k": k,
                            "seed": seed,
                            "alpha": alpha,
                            "sa_seed": sa_seed,
                            "nn_cost": nn_cost,
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
    progress_rows = []
    for (k, alpha), totals in progress.items():
        for iteration, count in enumerate(totals["counts"]):
            if count == 0:
                continue
            progress_rows.append(
                {
                    "k": k,
                    "alpha": alpha,
                    "iteration": iteration,
                    "runs": int(count),
                    "current_improvement_pct": (
                        totals["current_improvement"][iteration] / count
                    ),
                    "best_improvement_pct": (
                        totals["best_improvement"][iteration] / count
                    ),
                    "acceptance_pct": (
                        100 * totals["accepted"][iteration] / count
                        if iteration > 0
                        else math.nan
                    ),
                    "temperature": totals["temperature"][iteration] / count,
                }
            )
    return df, pd.DataFrame(progress_rows)


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
    for bars in ax.containers:
        ax.bar_label(bars, fmt="%.1f", padding=3)
    ax.set_ylim(bottom=0, top=ax.get_ylim()[1] * 1.1)
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=150)
    plt.close(ax.figure)


def plot_search_progress(progress: pd.DataFrame, iterations: int, path: Path) -> None:
    """Plota o custo atual e o melhor custo médio ao longo da busca."""
    ks = sorted(progress.k.unique())
    fig, axes = plt.subplots(
        len(ks), 1, figsize=(9, max(4, 3.5 * len(ks))), sharex=True, squeeze=False
    )
    for index, k in enumerate(ks):
        ax = axes[index, 0]
        for color_index, alpha in enumerate(sorted(progress.alpha.unique())):
            data = progress[(progress.k == k) & (progress.alpha == alpha)]
            color = f"C{color_index % 10}"
            ax.plot(
                data.iteration,
                data.best_improvement_pct,
                color=color,
                label=f"α={alpha:g} melhor",
            )
            ax.plot(
                data.iteration,
                data.current_improvement_pct,
                color=color,
                linestyle="--",
                alpha=0.7,
                label=f"α={alpha:g} atual",
            )
        ax.set_title(f"k = {k}")
        ax.set_ylabel("Melhoria sobre a rota inicial (%)")
        ax.grid(True, alpha=0.3)
        ax.legend()
    axes[-1, 0].set_xlabel("Iteração")
    axes[-1, 0].set_xlim(0, max(1, iterations))
    fig.suptitle("Evolução da busca: melhor rota e rota atual")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_acceptance_rate(progress: pd.DataFrame, iterations: int, path: Path) -> None:
    """Plota a taxa de aceitação suavizada para cada k e α."""
    ks = sorted(progress.k.unique())
    fig, axes = plt.subplots(
        len(ks), 1, figsize=(9, max(4, 3.5 * len(ks))), sharex=True, squeeze=False
    )
    window = max(1, iterations // 100)
    for index, k in enumerate(ks):
        ax = axes[index, 0]
        for color_index, alpha in enumerate(sorted(progress.alpha.unique())):
            data = progress[
                (progress.k == k) & (progress.alpha == alpha) & (progress.iteration > 0)
            ].sort_values("iteration")
            smoothed = data.acceptance_pct.rolling(window, min_periods=1).mean()
            ax.plot(
                data.iteration,
                smoothed,
                color=f"C{color_index % 10}",
                label=f"α={alpha:g}",
            )
        ax.set_title(f"k = {k}")
        ax.set_ylabel("Aceitação (%)")
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.legend()
    axes[-1, 0].set_xlabel("Iteração")
    axes[-1, 0].set_xlim(0, max(1, iterations))
    fig.suptitle(f"Taxa de aceitação (média móvel de {window} iterações)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_temperature(
    initial_temperature: float, alphas: list[float], iterations: int, path: Path
) -> None:
    """Plota a temperatura aplicada pelo resfriamento geométrico."""
    fig, ax = plt.subplots(figsize=(8, 4))
    iteration_values = range(iterations + 1)
    for alpha in sorted(alphas):
        temperatures = [
            initial_temperature * alpha**iteration for iteration in iteration_values
        ]
        ax.plot(iteration_values, temperatures, label=f"α={alpha:g}")
    ax.set_yscale("log")
    ax.set_xlabel("Iteração")
    ax.set_ylabel("Temperatura (escala log)")
    ax.set_title("Cronograma de resfriamento")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(title="Taxa de resfriamento")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    """Roda os experimentos e salva parâmetros, CSV, resumo e gráficos."""
    args, original = parse_args()
    env = environment()
    if original is not None:
        problems, warnings = check_environment(original.get("environment"), env)
        for warning in warnings:
            print(f"Aviso: {warning}", file=sys.stderr)
        if problems and not args.allow_env_mismatch:
            sys.exit(
                "Ambiente incompatível com o da execução original:\n  - "
                + "\n  - ".join(problems)
                + "\nInstale as mesmas versões (uv sync) ou use --allow-env-mismatch."
            )
    # Uma pasta por execução, <timestamp UTC>-<commit>[-dirty], para nunca sobrescrever
    # resultados anteriores e saber de qual versão do código cada um veio.
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"{timestamp}-{(env['commit'] or 'sem-commit')[:7]}"
    if env["uncommitted_changes"]:
        name += "-dirty"  # código diferente do commit: o resultado não é reproduzível
    results_dir = args.output / name
    results_dir.mkdir(parents=True)
    params = {k: v for k, v in vars(args).items() if k not in SCRIPT_OPTIONS}
    record = {"params": params, "environment": env}
    if original is not None:
        record["reproduces"] = args.params.parent.name
    (results_dir / "params.json").write_text(json.dumps(record, indent=2) + "\n")
    df, progress = run_experiments(args)
    df.to_csv(results_dir / "results.csv", index=False)
    progress.to_csv(results_dir / "search_progress.csv", index=False)

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
    plot_search_progress(progress, args.iterations, results_dir / "search_progress.png")
    plot_acceptance_rate(progress, args.iterations, results_dir / "acceptance_rate.png")
    plot_temperature(
        args.t0, args.alpha, args.iterations, results_dir / "temperature.png"
    )
    print(f"Resultados gravados em {results_dir}")
    if original is not None and (args.params.parent / "results.csv").exists():
        verdict = compare_results(
            args.params.parent / "results.csv", results_dir / "results.csv"
        )
        (results_dir / "comparison.txt").write_text(
            f"Comparação com {args.params.parent.name}: {verdict}\n"
        )
        print(f"Comparação com a execução original: {verdict}")


if __name__ == "__main__":
    main()
