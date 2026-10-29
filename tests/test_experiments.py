import importlib.util
import json
from pathlib import Path

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

# experiments/ não é um pacote: carrega o script pelo caminho.
_spec = importlib.util.spec_from_file_location(
    "experiments_run", Path(__file__).parents[1] / "experiments" / "run.py"
)
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

ENV = {
    "commit": "abc1234def",
    "uncommitted_changes": False,
    "python": "3.12.13",
    "packages": {"networkx": "3.7", "pandas": "3.0.6", "matplotlib": "3.11.2"},
}


def test_same_environment_has_no_problems():
    assert run.check_environment(ENV, ENV) == ([], [])


def test_python_patch_version_is_compatible():
    problems, _ = run.check_environment(ENV, {**ENV, "python": "3.12.1"})
    assert problems == []


def test_python_minor_or_package_version_is_incompatible():
    current = {
        **ENV,
        "python": "3.13.0",
        "packages": {**ENV["packages"], "pandas": "2.2"},
    }
    problems, _ = run.check_environment(ENV, current)
    assert len(problems) == 2


def test_different_commit_only_warns():
    problems, warnings = run.check_environment(ENV, {**ENV, "commit": "fff0000"})
    assert problems == [] and len(warnings) == 1


def test_params_file_sets_defaults_and_flags_override(tmp_path):
    record = {"params": {"k": [7], "iterations": 123}, "environment": ENV}
    path = tmp_path / "params.json"
    path.write_text(json.dumps(record))
    args, original = run.parse_args(["--params", str(path), "--iterations", "50"])
    assert args.k == [7] and args.iterations == 50 and original == record


def test_params_file_with_unknown_key_is_rejected(tmp_path):
    path = tmp_path / "params.json"
    path.write_text(json.dumps({"params": {"sa_seed": 0}}))
    with pytest.raises(SystemExit):
        run.parse_args(["--params", str(path)])


def test_compare_results_ignores_seconds(tmp_path):
    rows = {"k": [5, 6], "sa_cost": [10.0, 12.0], "opt_cost": [None, 12.0]}
    pd.DataFrame({**rows, "seconds": [0.1, 0.2]}).to_csv(tmp_path / "a.csv")
    pd.DataFrame({**rows, "seconds": [9.0, 9.0]}).to_csv(tmp_path / "b.csv")
    pd.DataFrame({**rows, "sa_cost": [10.0, 13.0], "seconds": [0, 0]}).to_csv(
        tmp_path / "c.csv"
    )
    assert run.compare_results(tmp_path / "a.csv", tmp_path / "b.csv").startswith(
        "idênticos"
    )
    assert run.compare_results(tmp_path / "a.csv", tmp_path / "c.csv").startswith(
        "1 de 2"
    )


def test_plot_by_k_labels_zero_values_and_starts_axis_at_zero(tmp_path, monkeypatch):
    closed_figures = []
    monkeypatch.setattr(run.plt, "close", closed_figures.append)
    df = pd.DataFrame({"k": [3], "alpha": [0.99], "deviation_pct": [0.0]})

    run.plot_by_k(df, "deviation_pct", "Desvio (%)", tmp_path / "deviation.png")

    ax = closed_figures[0].axes[0]
    assert [label.get_text() for label in ax.texts] == ["0.0"]
    assert ax.get_ylim()[0] == 0
    assert ax.get_ylim()[1] > 0


def test_experiment_progress_tracks_search_and_generates_charts(tmp_path):
    args, _ = run.parse_args(
        [
            "--grid-size",
            "6",
            "--k",
            "3",
            "--alpha",
            "0.99",
            "--seeds",
            "0",
            "--sa-seeds",
            "0",
            "--iterations",
            "20",
        ]
    )

    results, progress = run.run_experiments(args)

    assert len(progress) == 21
    assert progress.iloc[0].current_improvement_pct == 0
    assert progress.iloc[0].best_improvement_pct == 0
    assert pd.isna(progress.iloc[0].acceptance_pct)
    assert progress.iloc[-1].best_improvement_pct == pytest.approx(
        results.iloc[0].improvement_over_nn_pct
    )
    assert progress.best_improvement_pct.is_monotonic_increasing

    run.plot_search_progress(progress, args.iterations, tmp_path / "progress.png")
    run.plot_acceptance_rate(progress, args.iterations, tmp_path / "acceptance.png")
    run.plot_temperature(
        args.t0, args.alpha, args.iterations, tmp_path / "temperature.png"
    )
    assert all(
        (tmp_path / name).is_file()
        for name in ("progress.png", "acceptance.png", "temperature.png")
    )
