# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

The assignment spec is `docs/Enunciado.md` (Portuguese). Docstrings and UI text are in Portuguese; identifiers are in English.

## Commands

Packages are managed with **uv** (Python 3.12). Add dependencies with `uv add <pkg>` (`uv add --dev` for tooling) and run everything through `uv run …`; never use `pip install` directly.

```bash
uv sync                                     # install deps + the ktsp package
uv run pytest                               # all tests
uv run pytest tests/test_ktsp.py::test_name # single test
uv run ruff check . && uv run ruff format . # lint (incl. Google docstrings) + format
uv run ruff format --check .                # format check only (as in README)
uv run ktsp --help                          # CLI: solve one instance (see src/ktsp/cli.py)
uv run ktsp --city ibirapuita               # same, on the real map (meters)
uv run python scripts/download_street_map.py # re-download the real map (network) → src/ktsp/data/
uv run python app/api.py                    # API for the React app
cd web && npm install && npm run dev         # React app (requires Node.js)
uv run python experiments/run.py --help     # experiments (flags) → experiments/results/<timestamp>-<commit>[-dirty]/
```

## Architecture

`src/ktsp/` is the solver; `app/api.py` exposes it to the React UI in `web/`, and `experiments/` also consumes it, importing from the submodules directly (`ktsp/__init__.py` re-exports nothing).

- `instance.py` — `Instance` (graph, base, deliveries), `sample_instance(graph, k, rng)` (draws base + k deliveries from any graph) and the seeded synthetic grid-city generator (removes edges only if the graph stays connected). Every graph has node attr `pos` = (x, y) with y up (grid: `(col, -row)`; real map: `(lon, lat)`) and edge attr `weight`.
- `street_map.py` — `StreetMap` / `load_street_map()`: the real city, bairro Ibirapuitã (Alegrete-RS), read from `src/ktsp/data/ibirapuita.json` (package data, so the `ktsp` CLI finds it from any cwd). Weights are integer meters. The JSON is produced by `scripts/download_street_map.py` (OSM API, clipped to the bairro boundary, collinear degree-2 vertices removed) and committed, so instances never depend on the network.
- `distances.py` — `DistanceTable`, built via `build_distance_table(instance)`: Dijkstra from base and each delivery. **Index convention used everywhere: 0 = base, 1..k = deliveries.** A solution ("order") is a permutation of `1..k`.
- `solution.py` — `route_cost(order, table)` (hot path used by SA) and `Route.from_order`, which expands legs into the full vertex path.
- `annealing.py` — `anneal()` is a **generator yielding one `Step` per iteration** (step 0 = initial solution). The app keeps all steps for animation/replay; experiments take only the last. Neighbor = 2-opt reversal, geometric cooling. **Every run spends exactly `max_iterations` evaluations** (no temperature-based stop), so runs with different α/T0 are compared with the same budget; do not reintroduce an early stop. `tabu_tenure > 0` turns on an optional SA + Tabu hybrid (recently drawn 2-opt moves are skipped without spending budget); `tabu_tenure = 0` must stay byte-for-byte the plain SA, which the golden test guards. SA is the assignment's algorithm; the hybrid exists only for comparison (`--tabu-tenure`, API `tabuTenure` 0–100, UI "Modo de busca").
- `baselines.py` — nearest neighbor (also the SA starting solution) and brute-force optimum (k ≤ `MAX_BRUTE_FORCE_K`, else `ValueError`).
- `pipeline.py` — `solve(size, k, seed, sa_seed, params, city)`: the single generate+anneal path shared by the CLI (`cli.py`, entry point `ktsp`) and `app/api.py` (`saSeed`/`city` in the payload; UI defaults in `web/src/App.jsx` mirror `DEFAULT_*` here and `AnnealingParams`, except the city: the UI opens on `ibirapuita`, while `DEFAULT_CITY` stays `grid` so CLI, experiments and the golden test are unchanged). `city` is `grid` or `ibirapuita` (`CITIES`); on the real map `size` is ignored and `seed` only draws base + deliveries.
- `app/api.py` + `web/src/RouteMap.jsx` — the map is Leaflet: the API sends `positions` as a list indexed by vertex in `[lat, lng]` (the grid uses a `CRS.Simple` plane with `[y, x]`), and routes/edges as vertex ids. The real map loads OSM tiles live (needs internet).
- `experiments/run.py` — the experiment grid (k values, α, city seeds, a list of SA seeds, grid size, budget) comes from argparse flags with fixed defaults; every (city, α) runs once per SA seed. Metrics are relative to a reference: the brute-force optimum for k ≤ 8, otherwise the best route found across all runs of that city (`reference_is_optimum` flags which). It writes `params.json` (flags + git commit + Python/library versions), `results.csv` (raw, one row per run), `summary.csv` and PNG charts to a new folder `--output/<UTC timestamp>-<short commit>[-dirty]` (`-dirty` = uncommitted changes) (default `--output` is `experiments/results/`, git-ignored); it never overwrites an earlier run. `--params <run>/params.json` reruns a recorded experiment (file values become defaults, explicit flags win; flags in `SCRIPT_OPTIONS` are never recorded), aborts on Python major.minor or library version mismatch unless `--allow-env-mismatch`, only warns on commit/dirty differences, and compares results.csv (ignoring `seconds`) into `comparison.txt`. Tests in `tests/test_experiments.py` load the script by path, since `experiments/` is not a package. The default grid takes ~3 minutes.

## Determinism (required: same results on any machine)

- All randomness comes from two explicit seeds: `seed` (city) and `sa_seed` (SA), each passed to its own `random.Random`. Never use the global `random`, unseeded RNGs, time, or set/dict iteration order that depends on hashing of non-int keys.
- Python is pinned to 3.12 (`.python-version`, `requires-python`): `random`'s `randint`/`sample`/`shuffle` sequences may change across Python versions. `uv.lock` pins networkx.
- `tests/test_ktsp.py::test_default_run_matches_reference_values` holds golden values for the default run (and `test_street_map_run_matches_reference_values` for the real map). If an intentional algorithm change breaks it, update the values and rerun the experiments; otherwise treat a failure as a reproducibility bug.
- `seconds` in the experiment CSVs is the only machine-dependent output.

## The problem (from `docs/Enunciado.md`)

k-TSP for a motorcycle courier's shift, solved with **Simulated Annealing**, single objective.

- Input: a connected, weighted, **non-complete** graph (vertices = corners/delivery points, edges = streets with distances), a base vertex, and a vector `W` of exactly `k` delivery points.
- Output: the visiting order of `W`, the full vertex-by-vertex path, and the total distance.
- Objective: minimize total distance.
- Constraints: each point of `W` appears exactly once in the order; route starts and ends at the base; only existing edges are used; the route may pass through any vertex.
- Implication: the SA searches over permutations of `W`; the cost between consecutive points is the shortest-path distance in the graph (precompute shortest paths between base and `W` points, then expand legs to the full path for output).
- The group must generate its own test instances and run experiments with charts/tables, separating results from interpretation.

## Grading constraints that affect how code is written

- Python is mandatory (other languages only with the professor's explicit approval).
- Package/module structure should mirror the problem model (graph, instance, solution, SA algorithm, experiments).
- Clear, consistent names; docstrings, comments and README are graded.
- Atomic commits with clear messages (the repo uses Conventional Commits style: `docs:`, `build:`, …).
- Linters/formatters must be explicitly configured in the repository.
- Follow SOLID and YAGNI.
- AI use must be declared; config files such as this one, rules and hooks must live in the repo.
