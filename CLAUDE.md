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
uv run python app/api.py                    # API for the React app
cd web && npm install && npm run dev         # React app (requires Node.js)
uv run python experiments/run.py            # experiments → experiments/results/
```

## Architecture

`src/ktsp/` is the solver; `app/api.py` exposes it to the React UI in `web/`, and `experiments/` also consumes it, importing from the submodules directly (`ktsp/__init__.py` re-exports nothing).

- `instance.py` — `Instance` (graph, base, deliveries) and the seeded synthetic grid-city generator (removes edges only if the graph stays connected; nodes carry `pos`, edges `weight`).
- `distances.py` — `DistanceTable`, built via `build_distance_table(instance)`: Dijkstra from base and each delivery. **Index convention used everywhere: 0 = base, 1..k = deliveries.** A solution ("order") is a permutation of `1..k`.
- `solution.py` — `route_cost(order, table)` (hot path used by SA) and `Route.from_order`, which expands legs into the full vertex path.
- `annealing.py` — `anneal()` is a **generator yielding one `Step` per iteration** (step 0 = initial solution). The app keeps all steps for animation/replay; experiments take only the last. Neighbor = 2-opt reversal, geometric cooling.
- `baselines.py` — nearest neighbor (also the SA starting solution) and brute-force optimum (k ≤ `MAX_BRUTE_FORCE_K`, else `ValueError`).
- `experiments/run.py` — the experiment grid (k values, cooling rates α, seeds, grid size, iterations) is set by module-level constants at the top; it writes CSVs and PNG charts to `experiments/results/`.

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
