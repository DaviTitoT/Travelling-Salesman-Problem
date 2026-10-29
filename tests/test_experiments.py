import importlib.util
import json
from pathlib import Path

import pytest

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
